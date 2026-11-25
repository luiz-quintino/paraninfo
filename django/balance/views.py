from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import secrets

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from datetime import datetime
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404, JsonResponse
from django.db.models import Sum
from pathlib import Path

from config.constants import MONTHS
from utils import save_log, is_admin, is_app_admin, user_role
from .services.balance_calc import user_balance
from closing_jobs.models import BalanceClosingJob
from closing_jobs.services import enqueue_balance_closing

from config.constants import MESSAGE_TYPE_INFO, \
                            MESSAGE_TYPE_ERROR, \
                            MESSAGE_TYPE_CONFIRM, \
                            MESSAGE_TYPE_INPUT, \
                            MESSAGE_TYPE_WARNING

from products.models import tbCompra, tbParcelamento
from .models import tbRelatorio
from transaction.models import tbTransacao, tbExtratoConfig, tbExtrato
from transaction.attachments import get_comprovante_details
from home.models import tbLog, tbSessao
from django.db.models.functions import TruncMonth, TruncYear
from users.models import tbAssociados
from paraninfo_admin.models import tbComissao

from qrcode_generator import gera_qrcode, gerar_payload_pix

from config.menus import MENU_CONTABILIDADE_VER_EXTRATO, \
                        MENU_CONTABILIDADE_INADIMPLENTES, \
                        MENU_CONTABILIDADE_ASSINAR_LIVRO_CAIXA, \
                        MENU_CONTABILIDADE_LIVRO_CAIXA, \
                        MENU_CONTABILIDADE_EMITIR_COBRANCA, \
                        MENU_CONTABILIDADE_RECIBOS, \
                        MENU_CONTABILIDADE_RECIBOS_EMITIR, \
                        MENU_CONTABILIDADE_FECHAR_BALANCO, \
                        MENU_CONTABILIDADE_MENSALIDADDES, \
                        MENU_CONTABILIDADE_RESUMO_OPERACOES, \
                        MENU_MENU_CONTABILIDADE, \
                        MENU_VOLTAR


def get_pix_details(comissao_id):
    comissao = tbComissao.objects.filter(id=comissao_id).first()
    return {
            'chave_pix': comissao.chave_pix,              #'50945607000112',
            'nome_recebedor': comissao.nome_curto,  #'COMISSAO DE FORMATURA',
            'cidade': comissao.cidade,              #'Belo Horizonte',
            'txid': 'Mensalidade',
          }

@login_required
def balance_my_view(request, usuario):
    associado = get_object_or_404(tbAssociados, uuid=usuario)
    is_admin_ = is_admin(request)
    is_self = str(getattr(request.user, 'last_name', '')) == associado.uuid
    can_view_commission_payments = user_role(request) in {
        'presidente', 'vice-presidente', 'tesoureiro', 'fiscal',
    }
    if not is_self and (
        not (is_admin_ or can_view_commission_payments)
        or getattr(request, 'comissao', None) != associado.comissao
    ):
        raise PermissionDenied

    today = date.today()
    summary = user_balance(associado, today)

    # Cria QRCode
    next_payment_qrcode_url = None
    next_payment_pix_code = None
    if summary['next_payment'] is not None and summary['next_payment'] > 10:
        pix_details = get_pix_details(request.session['user_data']['comissao'])
        pix_details['valor'] = summary['next_payment']  # valor do pix no qrcode

        next_payment_pix_code = gerar_payload_pix(
            pix_key=pix_details['chave_pix'],
            merchant_name=pix_details['nome_recebedor'],
            merchant_city=pix_details['cidade'],
            amount=pix_details['valor'],
            txid=pix_details['txid'],
        )
        qrcode_path = gera_qrcode(
            **pix_details,
        )
        next_payment_qrcode_url = f"{settings.MEDIA_URL.rstrip('/')}/{qrcode_path}"

    context = {
        'associado': associado,
        'message': {'title': f'Meus pagamentos - {associado.nome_responsavel}'},
        'menu_options': [{'name': 'Voltar', 'url': '#', 'type': 'voltar'}],
        'today': today,
        'next_payment_qrcode_url': next_payment_qrcode_url,
        'next_payment_pix_code': next_payment_pix_code,
        **summary,
    }
    return render(request, 'balance/balance_my.html', context)


@login_required()
def emitir_recibo_view(request):
    """
    Render the emitir recibo view.
    """

    # Busca pagamentos associados por código de pagamento no período.
    extratos = tbExtrato.objects.filter(
        comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
        status=2,
        codigo_pagamento__isnull=False,
    ).order_by('-data')  # Ordena por data decrescente

    is_data_empty = not extratos.exists()  # Verifica se a queryset está vazia

    extrato_list = []
    for extrato in extratos:
        extrato_list.append({
            'id': extrato.id,
            'data': extrato.data.strftime('%d/%m/%Y') if extrato.data else None,
            'historico': extrato.historico,
            'credito': extrato.credito or '',
            'debito': extrato.debito or '',
            'transacao_key': extrato.transacao.key,
            'associado_nome': tbAssociados.objects.filter(
                comissao=extrato.comissao_id,
                codigo_pagamento=str(extrato.codigo_pagamento),
            ).values_list('nome_responsavel', flat=True).first() or '',
        })

    message = {'type': 'info', 'text': '', 'title': 'Emitir Recibo', 'function': ''}

    menu_options = [
        MENU_VOLTAR,
        # MENU_MENU_CONTABILIDADE,
        # MENU_CONTABILIDADE_RECIBOS_EMITIR

    ]

    if request.method == 'POST':
        # Busca a lista de extratos a serem ignorados
        linhas_ignoradas = request.POST.getlist('linhas_ignoradas', [])
        
        extratos_tamanho = len(extratos)
        if extratos_tamanho > len(linhas_ignoradas) and extratos_tamanho > 0:
            # cria log
            # log_id = save_log(request,
            #     description='tbExtrato',
            #     evento_log_id = 10  # log: Análise de movimentação
            # )

            # TODO: criar LOG, emitir recibo e atualizar status do extrato

            conunt_emitidos = 0
            for extrato in extratos:
                if extrato.id not in linhas_ignoradas:
                    # Atualiza o status do extrato para 3 (emitido)
                    conunt_emitidos += 1
                    # extrato.log_fechamento_id = request.user.id
                    # extrato.status = 3
                    # extrato.save()

            # Mensagem de sucesso
            message['text'] = f'Foram emitidos { conunt_emitidos } recibos!'
            message['type'] = MESSAGE_TYPE_INFO
            message['function'] = 'reloadPage()'

    context = {
        'is_data_empty': is_data_empty,
        'menu_options': menu_options,
        'message': message,
        'extrato_list': extrato_list,
    }
    
    return render(request, 'emitir_recibo.html', context)


@login_required()
def close_balance_view(request):
    """
        Faz o fechamento do mês
    """
    message = {'type': 'info', 'text': '', 'title': 'Fechamento de Balanço', 'function': ''}
    closing_notice = None
    closing_was_just_submitted = False
    if request.method == 'GET':
        closing_notice = request.session.pop('balance_closing_notice', None)
        closing_was_just_submitted = request.session.pop(
            'balance_closing_submitted', False
        )

    is_data_empty = False  # Variável para verificar se os dados estão vazios
    close_balance = True
    wrong_month = False

    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
        # MENU_CONTABILIDADE_FECHAR_BALANCO,
        # MENU_CONTABILIDADE_MENSALIDADDES,
    ]

    comissaodb = tbComissao.objects.filter(id=request.comissao).first()
    latest_closing_job = BalanceClosingJob.objects.filter(
        comissao_id=request.comissao,
    ).order_by('-created_at').first()
    closing_job_matches_period = bool(
        latest_closing_job
        and (latest_closing_job.year, latest_closing_job.month, latest_closing_job.sequence)
        == (comissaodb.ano, comissaodb.mes, comissaodb.sequence)
    )
    closing_job_blocks_retry = closing_job_matches_period and latest_closing_job.status in {
        BalanceClosingJob.PENDING,
        BalanceClosingJob.RUNNING,
        BalanceClosingJob.FAILED,
    }

    enclose_month = datetime.now().month
    enclose_month = enclose_month - 1 if enclose_month > 1 else 12

    skip_check = comissaodb.skip_month_check
    if skip_check !=1:
        # Verifica o mês correto antes de efetuar o fechamento
        if enclose_month != comissaodb.mes:
            if enclose_month > comissaodb.mes:
                message['text'] = f'Erro na sequência de fechamento. Esperado o mês: {comissaodb.mes}/{comissaodb.ano} '
            else:
                message['text'] = f'Aguarde o mês terminar para fazer o fechamento do mês referente à {comissaodb.mes}/{comissaodb.ano} '

            message['type'] = MESSAGE_TYPE_WARNING
            message['function'] = 'submitForm("formSuccess")'
            close_balance = False

            wrong_month = True


    if request.method == 'POST':
        if request.POST.get('success', ''):
            return redirect('balance:balance')

        if request.POST.get('close', ''):
            close_balance = True
        
        if request.POST.get('confirm', ''):
            submitted_token = request.POST.get('request_token', '')
            expected_token = request.session.get('balance_closing_request_token', '')
            valid_token = bool(expected_token and submitted_token) and secrets.compare_digest(
                submitted_token.encode('utf-8'),
                expected_token.encode('utf-8'),
            )
            if not valid_token:
                message['text'] = 'Requisição fora de contexto'
                message['type'] = MESSAGE_TYPE_WARNING
                request.session['balance_closing_notice'] = {
                    'type': message['type'],
                    'text': message['text'],
                    'title': message['title'],
                    'function': '',
                }
                return redirect('balance:fechar_balanco')

            # Token de uso único: recarregar ou reenviar este POST não repete o fechamento.
            request.session.pop('balance_closing_request_token', None)
            extratos = tbExtrato.objects.filter(
                comissao_id=request.comissao,
                data__year=comissaodb.ano,
                data__month=comissaodb.mes,
                status=2 # Extratos prontos para fechamento
            )

            if extratos.exists():
                allowed_roles = {'presidente', 'vice-presidente', 'tesoureiro'}
                if user_role(request) not in allowed_roles and not is_app_admin(request):
                    raise PermissionDenied

                latest_closing_job, created = enqueue_balance_closing(
                    comissao_id=request.comissao,
                    requested_by_user_id=request.user_id,
                    session_id=request.session.get('user_data', {}).get('sessao_id', 0),
                )
                if created:
                    # Mostra a página de acompanhamento sem popup que possa reenviar
                    # a confirmação ao executar seu callback ou ao ser recarregado.
                    request.session.pop('balance_closing_notice', None)
                    request.session['balance_closing_submitted'] = True
                    return redirect('balance:fechar_balanco')
                elif latest_closing_job.status == BalanceClosingJob.FAILED:
                    message['text'] = (
                        'A tentativa anterior falhou. Por segurança, não foi iniciada outra '
                        'tentativa automática. Revise o estado do banco antes de tentar novamente.'
                    )
                    message['type'] = MESSAGE_TYPE_ERROR
                elif latest_closing_job.status in {
                    BalanceClosingJob.PENDING,
                    BalanceClosingJob.RUNNING,
                }:
                    message['title'] = 'Fechamento já em andamento'
                    message['text'] = (
                        'Já existe um processo de fechamento em andamento '
                        f'(período {latest_closing_job.month}/{latest_closing_job.year}). '
                        'Aguarde a conclusão antes de solicitar novo fechamento.'
                    )
                    message['type'] = MESSAGE_TYPE_INFO
                else:
                    message['text'] = 'Já existe uma tarefa de fechamento para este período.'
                    message['type'] = MESSAGE_TYPE_INFO
                    message['function'] = 'window.location.reload()'

                # Preserve o aviso no redirect; a view monta o popup no próximo GET.
                request.session['balance_closing_notice'] = {
                    'type': message['type'],
                    'text': message['text'],
                    'title': message['title'],
                    'function': message['function'],
                }
                return redirect('balance:fechar_balanco')

            else:
                message['text'] = f'Não existem movimentação para fechamento para o mês {comissaodb.mes}/{comissaodb.ano}'
                message['type'] = MESSAGE_TYPE_WARNING
                message['function'] = 'submitForm("formSuccess")'
                close_balance = False
            
    elif not closing_job_blocks_retry:
        if not wrong_month:
            count_extrato_status_1 = tbExtrato.objects.filter(
                comissao_id=request.comissao,
                data__year=comissaodb.ano,
                data__month=comissaodb.mes,
                status=1  # Extratos com status 1 (pendente)
            ).count()

            if count_extrato_status_1 > 0:
                message['text'] = f'Existem {count_extrato_status_1} movimentações em análise, aguradando revisão. Tem certeza que deseja continuar com o fechamento para o mês {comissaodb.mes}/{comissaodb.ano}?'
                message['type'] = MESSAGE_TYPE_CONFIRM
                message['function'] = 'submitForm("formCloseBalance")'
                close_balance = False

    closing_job_matches_period = bool(
        latest_closing_job
        and (latest_closing_job.year, latest_closing_job.month, latest_closing_job.sequence)
        == (comissaodb.ano, comissaodb.mes, comissaodb.sequence)
    )
    closing_job_blocks_retry = closing_job_matches_period and latest_closing_job.status in {
        BalanceClosingJob.PENDING,
        BalanceClosingJob.RUNNING,
        BalanceClosingJob.FAILED,
    }

    if close_balance and not closing_job_blocks_retry:
        count_extrato_status_2 = tbExtrato.objects.filter(
                comissao_id=request.comissao,
                data__year=comissaodb.ano,
                data__month=comissaodb.mes,
                status=2  # Extratos com status 2 (prontos para fechamento)
            ).count()

        if count_extrato_status_2 > 0:
            message['text'] = f'Existem {count_extrato_status_2} movimentações prontas para fechamento. Tem certeza que deseja continuar com o fechamento para o mês {comissaodb.mes}/{comissaodb.ano}?'
            message['type'] = MESSAGE_TYPE_CONFIRM
            message['function'] = 'submitForm("formConfirmCloseBalance")'

        else:
            is_data_empty = True
            message['text'] = f'Não existem movimentação para fechamento para o mês {comissaodb.mes}/{comissaodb.ano}'
            message['type'] = MESSAGE_TYPE_WARNING
            message['function'] = 'submitForm("formSuccess")'
            close_balance = False

    # O aviso do POST deve prevalecer sobre as validações normais da página no GET.
    if closing_notice:
        message.update(closing_notice)

    # Uma solicitação aceita já está sendo acompanhada no painel de status; não
    # exiba popup nem confirmação de um novo fechamento nessa página.
    if closing_was_just_submitted or (
        closing_job_blocks_retry
        and latest_closing_job.status in {
            BalanceClosingJob.PENDING,
            BalanceClosingJob.RUNNING,
        }
        and not closing_notice
    ):
        message['text'] = ''
        message['function'] = ''

    request_token = request.session.get('balance_closing_request_token')
    if not request_token:
        request_token = secrets.token_urlsafe(32)
        request.session['balance_closing_request_token'] = request_token

    context = {
        'menu_options': menu_options,
        'message': message,
        'is_data_empty': is_data_empty,
        'closing_job': latest_closing_job,
        'request_token': request_token,
    }
    
    return render(request, 'close_balance.html', context)

@login_required()
def balance_extract_view(request):
    """
        Render the balance view.
    """
    message = {'type': 'info', 'text': '', 'title': 'Extrato de movimentações', 'function': ''}
    is_admin_user = is_admin(request)
    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
        # MENU_CONTABILIDADE_MENSALIDADDES,
    ]

    if user_role(request) in ['presidente', 'vice-presidente', 'tesoureiro'] or is_app_admin(request):
        menu_options.append(MENU_CONTABILIDADE_FECHAR_BALANCO)
    
    comissao_id = request.comissao if request.comissao else 1
    extratos = tbExtrato.objects.filter(comissao_id=comissao_id)

    # Extrair meses e anos únicos da comissão atual
    meses_anos = extratos.filter(data__isnull=False).annotate(
        ano=TruncYear('data'),  # Extrai o ano
        mes=TruncMonth('data')  # Extrai o mês
    ).values('ano', 'mes').distinct().order_by('-ano', '-mes')
    
    # Preparar os dados para o template
    periodos = [
        {
            'ano': item['ano'].year,
            'mes': item['mes'].month,
            'combinado': f"{MONTHS.get(item['mes'].month)} de {item['ano'].year}",
        }
        for item in meses_anos
    ]

    # Sem filtro explícito, seleciona o período mais recente (índice 1).
    search_query = request.GET.get('periodo_index')
    if search_query is None:
        search_query = '1' if periodos else 'todos'

    # "todos" mantém o extrato completo.
    if search_query != 'todos':
        try:
            periodo_index = int(search_query) - 1
            if periodo_index < 0 or periodo_index >= len(periodos):
                raise IndexError
            periodo = periodos[periodo_index]
        except (ValueError, IndexError):
            search_query = 'todos'
            message['text'] = 'Período inválido; exibindo todos.'
            message['type'] = 'error'
        else:
            extratos = extratos.filter(
                data__year=periodo['ano'],
                data__month=periodo['mes'],
            )

    status_options = [
        {'value': '', 'label': 'Todos os status'},
        {'value': 'novo', 'label': 'Novo'},
        {'value': str(tbExtrato.STATUS_EXTRATO_CANCELADO), 'label': 'Cancelado'},
        {'value': str(tbExtrato.STATUS_EXTRATO_CLASSIFICADO), 'label': 'Classificado'},
        {'value': str(tbExtrato.STATUS_EXTRATO_INCORPORADO), 'label': 'Revisado'},
        {'value': str(tbExtrato.STATUS_EXTRATO_BALANCO_FECHADO), 'label': 'Balanço fechado'},
    ]

    if is_admin_user:
        selected_status = request.GET.get('status', '')
        if selected_status == 'novo':
            extratos = extratos.filter(status__isnull=True)
        elif selected_status in {
            str(tbExtrato.STATUS_EXTRATO_CANCELADO),
            str(tbExtrato.STATUS_EXTRATO_CLASSIFICADO),
            str(tbExtrato.STATUS_EXTRATO_INCORPORADO),
            str(tbExtrato.STATUS_EXTRATO_BALANCO_FECHADO),
        }:
            extratos = extratos.filter(status=int(selected_status))
        else:
            selected_status = ''
    else:
        selected_status = str(tbExtrato.STATUS_EXTRATO_BALANCO_FECHADO)
        extratos = extratos.filter(status=tbExtrato.STATUS_EXTRATO_BALANCO_FECHADO)

    extrato_list = []
    for index, extrato in enumerate(extratos):
        extrato_list.append({
            'indice': index + 1,  # Índice começa em 1
            'id': extrato.id,
            'data': extrato.data.strftime('%d/%m/%Y') if extrato.data else None,
            'historico': extrato.historico,
            'credito': extrato.credito or '',
            'debito': extrato.debito or '',
            'transacao_key': extrato.transacao.key_name if extrato.transacao else '',
            'codigo_pagamento': extrato.codigo_pagamento or '',
            'comprovante': extrato.comprovante,
            'status': extrato.status or '',
        })

    comissao = tbComissao.objects.filter(
        id=request.comissao,
    ).first()

    fechamento = f'nº {comissao.sequence} referente a {comissao.mes}/{comissao.ano}'
    
    context = {
        'menu_options': menu_options,
        'message': message,
        'extrato_list': extrato_list,
        'periodos': periodos,
        'search_query': search_query,
        'is_admin_user': is_admin_user,
        'status_options': status_options,
        'selected_status': selected_status,
        'fechamento': fechamento,
    }
    return render(request, 'balance_extract.html', context)


@login_required()
def balance_overview(request):
    """Exibe as transações mensais de uma comissão em modo somente leitura."""
    message = {'type': 'info', 'text': '', 'title': 'Resumo de operações mensais', 'function': ''}
    
    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
        # MENU_CONTABILIDADE_MENSALIDADDES,
    ]

    # if user_role(request) in ['presidente', 'vice-presidente', 'tesoureiro'] or is_app_admin(request):
    #     menu_options.append(MENU_CONTABILIDADE_FECHAR_BALANCO)

    comissao_id = getattr(request, 'comissao', None)
    transactions = tbTransacao.objects.filter(comissao_id=comissao_id)

    available_months = [
        (period.year, period.month)
        for period in transactions.dates('data', 'month', order='DESC')
    ]
    available_month_options = [{'value': 'totais', 'label': 'Totais'}]
    available_month_options.extend(
        {
            'value': f'{year:04d}-{month:02d}',
            'label': f'{MONTHS[month].title()} de {year}',
        }
        for year, month in available_months
    )
    selected_month = None
    show_totals = False

    requested_month = request.GET.get('month', '')
    if requested_month == 'totais' and available_months:
        show_totals = True
    elif requested_month:
        try:
            year, month = (int(part) for part in requested_month.split('-', 1))
            if 1 <= month <= 12 and (year, month) in available_months:
                selected_month = (year, month)
        except (ValueError, TypeError):
            pass

    if selected_month is None and available_months and not show_totals:
        selected_month = available_months[0]

    selected_transactions = tbTransacao.objects.none()
    selected_sequence = None
    period_label = ''
    previous_month = None
    next_month = None

    if show_totals:
        period_label = 'Totais'
        omitted_names = ['Saldo inicial', 'Saldo bloqueado']
        latest_month = available_months[0]
        latest_year, latest_month_number = latest_month
        latest_sequence = (
            transactions.filter(
                data__year=latest_year,
                data__month=latest_month_number,
            )
            .order_by('-sequencia')
            .values_list('sequencia', flat=True)
            .first()
        )

        balance_names = ['Saldo CC', 'Saldo CC + Apl', 'Saldo Total CC + Apl']
        total_rows = (
            transactions.filter(transacao__isnull=False)
            .exclude(transacao__key_name__in=omitted_names)
            .exclude(transacao__key_name__in=balance_names)
            .values('transacao__key_name', 'transacao__color_name')
            .annotate(total=Sum('valor'))
            .order_by('transacao__key_name')
        )
        transaction_rows = [
            {
                'data': None,
                'transacao_id': item['transacao__key_name'] or '—',
                'valor': item['total'],
                'color_name': item['transacao__color_name'],
            }
            for item in total_rows
        ]

        if latest_sequence is not None:
            latest_balances = (
                transactions.filter(
                    data__year=latest_year,
                    data__month=latest_month_number,
                    sequencia=latest_sequence,
                    transacao__key_name__in=balance_names,
                )
                .select_related('transacao')
                .order_by('id')
            )
            transaction_rows.extend(
                {
                    'data': item.data,
                    'transacao_id': item.transacao.key_name if item.transacao else '—',
                    'valor': item.valor,
                    'color_name': item.transacao.color_name if item.transacao else None,
                }
                for item in latest_balances
            )

    elif selected_month:
        year, month = selected_month
        period_label = f'{MONTHS[month].title()} de {year}'
        month_transactions = transactions.filter(data__year=year, data__month=month)
        selected_sequence = (
            month_transactions.order_by('-sequencia')
            .values_list('sequencia', flat=True)
            .first()
        )

        # O período visível é escolhido por ano/mês; os registros são filtrados pela sequência.
        if selected_sequence is not None:
            selected_transactions = (
                transactions.filter(sequencia=selected_sequence)
                .select_related('transacao')
                .order_by('id')
            )

        month_index = available_months.index(selected_month)
        if month_index + 1 < len(available_months):
            year_, month_ = available_months[month_index + 1]
            previous_month = f'{year_:04d}-{month_:02d}'
        if month_index > 0:
            year_, month_ = available_months[month_index - 1]
            next_month = f'{year_:04d}-{month_:02d}'

    if not show_totals:
        transaction_rows = [
            {
                'data': item.data,
                'transacao_id': item.transacao.key_name if item.transacao else '—',
                'valor': item.valor,
                'color_name': item.transacao.color_name if item.transacao else None,
            }
            for item in selected_transactions
        ]

    context = {
        'message': message,
        'menu_options': menu_options,
        'transactions': transaction_rows,
        'period_label': period_label,
        'show_totals': show_totals,
        'selected_month': (
            'totais' if show_totals else (
                f'{selected_month[0]:04d}-{selected_month[1]:02d}'
                if selected_month else ''
            )
        ),
        'previous_month': previous_month,
        'next_month': next_month,
        'selected_sequence': selected_sequence,
        'has_months': bool(available_months),
    }
    context['available_month_options'] = available_month_options
    return render(request, 'balance/balance_overview.html', context)

def livro_caixa(request):
    """Lista os relatórios PDF de fechamento da comissão do usuário."""
    message = {'type': 'info', 'text': '', 'title': 'Extrato de movimentações', 'function': ''}
    
    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
        # MENU_CONTABILIDADE_MENSALIDADDES,
    ]

    # if user_role(request) in ['presidente', 'vice-presidente', 'tesoureiro'] or is_app_admin(request):
    #     menu_options.append(MENU_CONTABILIDADE_FECHAR_BALANCO)
    
    reports = tbRelatorio.objects.none()
    if request.comissao:
        reports = tbRelatorio.objects.filter(
            comissao_id=request.comissao,
            arquivo__iendswith='.pdf',
        ).order_by('-data', '-sequencia')

    context = {
        'reports': reports,
        'menu_options': menu_options,
        'message': message,
    }
    return render(request, 'balance/livro_caixa.html', context)


@login_required()
def balance_report_file(request, report_id):
    """Abre um PDF após validar comissão, extensão e caminho dentro de MEDIA_ROOT."""
    report = get_object_or_404(
        tbRelatorio,
        id=report_id,
        comissao_id=request.comissao,
    )
    if not report.arquivo or not report.pasta or Path(report.arquivo).name != report.arquivo:
        raise Http404('Relatório não encontrado.')

    filename = Path(report.arquivo)
    if filename.suffix.lower() != '.pdf':
        raise Http404('Relatório não encontrado.')

    media_root = Path(settings.MEDIA_ROOT).resolve()
    report_folder = Path(report.pasta)
    if report_folder.parts and report_folder.parts[0].lower() == 'media':
        report_folder = Path(*report_folder.parts[1:])

    file_path = (media_root / report_folder / filename).resolve()
    try:
        file_path.relative_to(media_root)
    except ValueError as error:
        raise Http404('Relatório não encontrado.') from error

    if not file_path.is_file():
        raise Http404('Relatório não encontrado.')

    return FileResponse(
        file_path.open('rb'),
        content_type='application/pdf',
        as_attachment=False,
        filename=filename.name,
    )


@login_required()
def get_extrato_details(request, extrato_id):
    """
        Retorna os detalhes de um extrato específico em formato JSON.
    """
    extrato = get_object_or_404(
        tbExtrato.objects.select_related('transacao'),
        id=extrato_id,
        comissao_id=request.comissao,
    )

    def log_details(log_id):
        if not log_id:
            return {'data': '', 'name': ''}

        log = tbLog.objects.filter(id=log_id).first()
        if not log:
            return {'data': '', 'name': ''}

        sessao = tbSessao.objects.filter(
            id=log.sessao_ativa_id
        ).select_related('usuario').first()
        nome = (
            sessao.usuario.nome_responsavel
            if sessao and sessao.usuario else ''
        )
        return {
            'data': log.data.strftime('%d/%m/%Y, %H:%M:%S') if log.data else '',
            'name': nome,
        }
    
    associado_nome = ''
    if extrato.codigo_pagamento is not None:
        payment_code = str(extrato.codigo_pagamento).strip()
        if payment_code.isdigit():
            equivalent_codes = {
                payment_code.zfill(width)
                for width in range(len(payment_code), 6)
            }
            associado_nome = tbAssociados.objects.filter(
                comissao=extrato.comissao_id,
                codigo_pagamento__in=equivalent_codes,
            ).values_list('nome_responsavel', flat=True).first() or ''

    if not associado_nome:
        associado_nome = extrato.nome or ''

    context = {
        'id': extrato.id,
        'data': extrato.data.strftime('%d/%m/%Y') if extrato.data else '',
        'historico': extrato.historico,
        'credito': extrato.credito or '',
        'debito': extrato.debito or '',
        'transacao': extrato.transacao.key_name if extrato.transacao else '',
        'nome': associado_nome ,
        'registro_log': log_details(extrato.log_registro_id),
        'associacao_log': log_details(extrato.log_associacao_id),
        'fechamento_log': log_details(extrato.log_fechamento_id),
        'status': extrato.status,
        'can_return_to_review': (
            user_role(request) == 'presidente'
            and extrato.status == tbExtrato.STATUS_EXTRATO_INCORPORADO
        ),
        'comprovante': get_comprovante_details(extrato),
    }

    return JsonResponse(context)