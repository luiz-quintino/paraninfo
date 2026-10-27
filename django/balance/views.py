from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from datetime import datetime
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404, JsonResponse
from pathlib import Path

from config.constants import MONTHS
from utils import save_log, is_admin, is_app_admin, user_role
from .services.balance_calc import month_enclosed, user_balance

from config.constants import MESSAGE_TYPE_INFO, \
                            MESSAGE_TYPE_ERROR, \
                            MESSAGE_TYPE_CONFIRM, \
                            MESSAGE_TYPE_INPUT, \
                            MESSAGE_TYPE_WARNING

from products.models import tbCompra, tbParcelamento
from .models import tbRelatorio
from transaction.models import tbTransacao, tbExtratoConfig, tbExtrato
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
    if not is_self and (not is_admin_ or getattr(request, 'comissao', None) != associado.comissao):
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

    # Buscars no extrato os pagamentos de usuario tbExtrato.associado_id not null e tbExtrato.status == 2
    extratos = tbExtrato.objects.filter(
        comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
        status=2,
        associado_id__isnull=False  # Filtra para incluir apenas extratos com associado_id
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
            'associado_nome': extrato.associado.nome_responsavel,
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
    Render the close balance view.
    """
    message = {'type': 'info', 'text': '', 'title': 'Fechamento de Balanço', 'function': ''}
    is_data_empty = False  # Variável para verificar se os dados estão vazios
    close_balance = True
    wrong_month = False

    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
        MENU_CONTABILIDADE_FECHAR_BALANCO,
        # MENU_CONTABILIDADE_MENSALIDADDES,
    ]

    comissaodb = tbComissao.objects.filter(id=request.comissao).first()

    enclose_month = datetime.now().month
    enclose_month = enclose_month - 1 if enclose_month > 1 else 12

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
            #***********************************************************************************************
            # Realiza o fechamento mensal do mês anterior
            #***********************************************************************************************

            comissao = {'sequence': comissaodb.sequence,
                        'title': comissaodb.nome_comissao,           # 'COMISSÃO DE FORMATURA DOS SÓCIOS TURMAS DO 6º ANO 2023'
                        'inscricao': comissaodb.inscricao,           # '1478340/001-2'
                        'cnpj': comissaodb.cnpj,                     # '50.945.607/0001-12'
                        'comissao_id': request.comissao,
                        'year': comissaodb.ano,
                        'month': comissaodb.mes,
            }

            # Filtra os extratos do mês anterior
            extratos = tbExtrato.objects.filter(
                comissao_id=request.comissao,
                data__year=comissaodb.ano,
                data__month=comissaodb.mes,
                status=2 # Extratos prontos para fechamento
            )

            if extratos:
                month_enclosed(comissao, extratos)

                message['text'] = f'Fechamento realizado com sucesso. O relatório encontra-se disponível no menu Resumo de operações'
                message['type'] = MESSAGE_TYPE_INFO
                message['function'] = 'submitForm("formSuccess")'
                close_balance = False
                

            else:
                message['text'] = f'Não existem movimentação para fechamento para o mês {comissaodb.mes}/{comissaodb.ano}'
                message['type'] = MESSAGE_TYPE_WARNING
                message['function'] = 'submitForm("formSuccess")'
                close_balance = False
            
    else:
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

    if close_balance:
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

    context = {
        'menu_options': menu_options,
        'message': message,
        'is_data_empty': is_data_empty
    }
    
    return render(request, 'close_balance.html', context)

@login_required()
def balance_view(request):
    """
        Render the balance view.
    """
    message = {'type': 'info', 'text': '', 'title': 'Extrato de movimentações', 'function': ''}
    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
        # MENU_CONTABILIDADE_MENSALIDADDES,
    ]

    if user_role(request) in ['presidente', 'vice-presidente', 'tesoureiro'] or is_app_admin(request):
        menu_options.append(MENU_CONTABILIDADE_FECHAR_BALANCO)
    
    # Extrair meses e anos únicos
    meses_anos = tbExtrato.objects.annotate(
        ano=TruncYear('data'),  # Extrai o ano
        mes=TruncMonth('data')  # Extrai o mês
    ).values('ano', 'mes').distinct()
    
    # Preparar os dados para o template
    periodos = [{'ano': item['ano'].year, 'mes': item['mes'].month, 'combinado':f"{MONTHS.get(item['mes'].month)} de {item['ano'].year}"} for item in meses_anos][::-1]
    
    data_atual = datetime.now()  # Obtém a data atual como um objeto datetime
    mes_atual = data_atual.month  # Obtém o mês atual
    ano_atual = data_atual.year  # Obtém o ano atual

    # Obtem o o filtro de período do request, se existir
    search_query = request.GET.get('periodo_index', '1')  # Obtém o texto do filtro

    try:
        # Tenta converter o filtro em um inteiro
        periodo_index = int(search_query) - 1
        if periodo_index < 0 or periodo_index >= len(periodos):
            message['text'] = "Período inválido"
            message['type'] = 'error'
        mes_atual = periodos[periodo_index]['mes']
        ano_atual = periodos[periodo_index]['ano']
    except (ValueError, IndexError):
        message['text'] = "Período inválido"
        message['type'] = 'error'
        

    # Filtra os registros de tbExtrato para o mês e ano da data atual
    extratos = tbExtrato.objects.filter(
        comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
        status=2,
        data__year=ano_atual,  # Filtra pelo ano
        data__month=mes_atual  # Filtra pelo mês
    )

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
            'associado_id': extrato.associado_id if extrato.associado_id else '',
        })
        
    context = {
        'menu_options': menu_options,
        'message': message,
        'extrato_list': extrato_list,
        'periodos': periodos,
        'search_query': search_query,
    }
    return render(request, 'balance.html', context)


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

    if user_role(request) in ['presidente', 'vice-presidente', 'tesoureiro'] or is_app_admin(request):
        menu_options.append(MENU_CONTABILIDADE_FECHAR_BALANCO)

    comissao_id = getattr(request, 'comissao', None)
    transactions = tbTransacao.objects.filter(comissao_id=comissao_id)

    available_months = [
        (period.year, period.month)
        for period in transactions.dates('data', 'month', order='DESC')
    ]
    available_month_options = [
        {
            'value': f'{year:04d}-{month:02d}',
            'label': f'{MONTHS[month].title()} de {year}',
        }
        for year, month in available_months
    ]
    selected_month = None

    requested_month = request.GET.get('month', '')
    if requested_month:
        try:
            year, month = (int(part) for part in requested_month.split('-', 1))
            if 1 <= month <= 12 and (year, month) in available_months:
                selected_month = (year, month)
        except (ValueError, TypeError):
            pass

    if selected_month is None and available_months:
        selected_month = available_months[0]

    selected_transactions = tbTransacao.objects.none()
    selected_sequence = None
    period_label = ''
    previous_month = None
    next_month = None

    if selected_month:
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
                .order_by('data', 'transacao__key_name', 'id')
            )

        month_index = available_months.index(selected_month)
        if month_index + 1 < len(available_months):
            year_, month_ = available_months[month_index + 1]
            previous_month = f'{year_:04d}-{month_:02d}'
        if month_index > 0:
            year_, month_ = available_months[month_index - 1]
            next_month = f'{year_:04d}-{month_:02d}'

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
        'selected_month': (
            f'{selected_month[0]:04d}-{selected_month[1]:02d}'
            if selected_month else ''
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

    if user_role(request) in ['presidente', 'vice-presidente', 'tesoureiro'] or is_app_admin(request):
        menu_options.append(MENU_CONTABILIDADE_FECHAR_BALANCO)
    
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
    registro_user = None
    associacao_user = None
    fechamento_user = None

    extrato = get_object_or_404(tbExtrato, id=extrato_id)
    registro = get_object_or_404(tbLog, id=extrato.log_registro_id) if extrato.log_registro_id else None
    associacao = get_object_or_404(tbLog, id=extrato.log_associacao_id) if extrato.log_associacao_id else None
    fechamento = get_object_or_404(tbLog, id=extrato.log_fechamento_id) if extrato.log_fechamento_id else None

    if registro:
        registro_user = get_object_or_404(tbSessao, id=registro.sessao_ativa_id) if registro else {}
    
    if associacao:
        associacao_user = get_object_or_404(tbSessao, id=associacao.sessao_ativa_id) if associacao else {}

    if fechamento:
        fechamento_user = get_object_or_404(tbSessao, id=fechamento.sessao_ativa_id) if fechamento else {}
    
    if extrato.associado_id:
        associado_nome = extrato.associado.nome_responsavel or ''
    else:
        associado_nome = ''

    context = {
        'id': extrato.id,
        'data': extrato.data.strftime('%d/%m/%Y') if extrato.data else '',
        'historico': extrato.historico,
        'credito': extrato.credito or '',
        'debito': extrato.debito or '',
        'transacao': extrato.transacao.key or '',
        'nome': associado_nome ,
        'registro_log':   {'data': registro.data.strftime('%d/%m/%Y, %H:%M:%S') or '',   'name': registro_user.usuario.nome_responsavel or ''},     #extrato.log_registro_id or '',
        'associacao_log': {'data': associacao.data.strftime('%d/%m/%Y, %H:%M:%S') or '', 'name': associacao_user.usuario.nome_responsavel or ''},     #extrato.log_associacao_id or '',
        'fechamento_log': {'data': fechamento.data.strftime('%d/%m/%Y, %H:%M:%S') or '', 'name': fechamento_user.usuario.nome_responsavel} or '',     #extrato.log_fechamento_id or ''
    }

    return JsonResponse(context)