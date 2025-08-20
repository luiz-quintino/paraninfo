from django.shortcuts import render
from transaction.models import tbTransacao, tbExtratoConfig, tbExtrato
from home.models import tbLog, tbSessao
from datetime import datetime
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models.functions import TruncMonth, TruncYear

from config.constants import MONTHS
from transaction.utils import save_log
from .services.balance_calc import month_enclosed

from config.constants import MESSAGE_TYPE_INFO, \
                            MESSAGE_TYPE_ERROR, \
                            MESSAGE_TYPE_CONFIRM, \
                            MESSAGE_TYPE_INPUT, \
                            MESSAGE_TYPE_WARNING

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

# Função para verificar se o usuário pertence ao grupo 'admin'
def is_sys_admin(user):
    is_admin = user.groups.filter(name='sys-admin').exists() or \
                user.groups.filter(name='app-admin').exists() or \
                user.groups.filter(name='master').exists()
    return is_admin

@user_passes_test(is_sys_admin)
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
        MENU_MENU_CONTABILIDADE,
        MENU_CONTABILIDADE_RECIBOS_EMITIR

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

@user_passes_test(is_sys_admin)
def close_balance_view(request):
    """
    Render the close balance view.
    """
    message = {'type': 'info', 'text': '', 'title': 'Fechamento de Balanço', 'function': ''}
    is_data_empty = False  # Variável para verificar se os dados estão vazios
    close_balance = True

    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_MENSALIDADDES,
        MENU_CONTABILIDADE_FECHAR_BALANCO,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
    ]

    if request.method == 'POST':
        if request.POST.get('close', ''):
            close_balance = True
        
        if request.POST.get('confirm', ''):
            # Realiza o fechamento mensal do mês anterior
            month_enclosed(request.comissao, datetime.now().year, datetime.now().month - 1)
            
    else:
        count_extrato_status_1 = tbExtrato.objects.filter(
            comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
            status=1  # Extratos com status 1 (pendente)
        ).count()

        if count_extrato_status_1 > 0:
            message['text'] = f'Existem {count_extrato_status_1} movimentações em análise, aguradando revisão. Tem certeza que deseja continuar com o fechamento?'
            message['type'] = MESSAGE_TYPE_CONFIRM
            message['function'] = 'submitForm("formCloseBalance")'
        close_balance = False

    if close_balance:
        count_extrato_status_2 = tbExtrato.objects.filter(
                comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
                status=2  # Extratos com status 2 (prontos para fechamento)
            ).count()

        if count_extrato_status_2 > 0:
            message['text'] = f'Existem {count_extrato_status_2} movimentações prontas para fechamento. Tem certeza que deseja continuar com o fechamento?'
            message['type'] = MESSAGE_TYPE_CONFIRM
            message['function'] = 'submitForm("formConfirmCloseBalance")'

        else:
            is_data_empty = True

        
        

    context = {
        'menu_options': menu_options,
        'message': message,
        'is_data_empty': is_data_empty
    }
    
    return render(request, 'close_balance.html', context)

@user_passes_test(is_sys_admin)
def balance_view(request):
    """
    Render the balance view.
    """

    message = {'type': 'info', 'text': '', 'title': 'Extrato de movimentações', 'function': ''}

    menu_options = [
        MENU_VOLTAR,
        MENU_CONTABILIDADE_RESUMO_OPERACOES,
        MENU_CONTABILIDADE_VER_EXTRATO,
        MENU_CONTABILIDADE_MENSALIDADDES,
        MENU_CONTABILIDADE_FECHAR_BALANCO,
        MENU_CONTABILIDADE_LIVRO_CAIXA,
    ]
    
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
            'transacao_key': extrato.transacao.key,
            'associado_id': extrato.associado_id if extrato.associado_id else '',
            'cor': extrato.transacao.color_name
        })
        
    context = {
        'menu_options': menu_options,
        'message': message,
        'extrato_list': extrato_list,
        'periodos': periodos,
        'search_query': search_query,
    }
    return render(request, 'balance.html', context)


@user_passes_test(is_sys_admin)
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

    data = {
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

    return JsonResponse(data)