from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from datetime import datetime
from decimal import Decimal
import pandas as pd
import json
import os
import re
from .models import tbExtratoConfig, tbExtrato, tbTransacao, tbBoleto, tbResumoComissao, tbComissao, lstBoletoStatus
from users.models import tbAssociados
from config.constants import MESSAGE_TYPE_INFO, \
                                MESSAGE_TYPE_ERROR, \
                                    MESSAGE_TYPE_WARNING, \
                                        MESSAGE_TYPE_SUCCESS, \
                                            MESSAGE_TYPE_CONFIRM

from utils import  convert_date, save_log, get_user_by_responsible_name

from .services.imports import process_sicoob_input_txt, process_sicoob_input_xls, import_boletos_xls, identify_transaction
                    
from config.menus import    MENU_VOLTAR, \
                            MENU_BALANCE_IMPORTAR_EXTRATO, \
                            MENU_BALANCE_ENTRADA_MANUAL, \
                            MENU_BALANCE_ANALISAR_MOVIMENTACAO, \
                            MENU_BALANCE_ACEITAR_ENTRADAS_EXTRATO, \
                            MENU_BALANCE_ACEITAR_EXTRATO, \
                            MENU_BALANCE_EXTRATO, \
                            MENU_BALANCE_SALVAR_MOVIMENTACOES, \
                            MENU_BALANCE_REVISAR_ANALISE, \
                            MENU_BALANCE_FECHAR_ANALISE, \
                            MENU_BALANCE_BOLETO, \
                            MENU_BALANCE_BOLETO_ADICIONAR, \
                            MENU_BALANCE_BOLETO_MANUAL, \
                            MENU_BALANCE_BOLETO_IMPORTAR, \
                            MENU_BALANCE_BOLETO_SALVAR, \
                            MENU_BALANCE_FECHAR_ANALISE_CONFIRMAR

# Função para verificar se o usuário pertence ao grupo 'admin'
def is_sys_admin(user):
    is_admin = user.groups.filter(name='sys-admin').exists() or \
                user.groups.filter(name='app-admin').exists() or \
                user.groups.filter(name='master').exists()
    return is_admin

@user_passes_test(is_sys_admin)
def boleto_manual_view(request):
    """
        Adiciona boleto manualmente
    """
    message = {'type': 'info', 'text': '', 'title': 'Boleto manual', 'function': ''}
    
    # Cria side menu
    menu_options = [
        MENU_VOLTAR,
        MENU_BALANCE_EXTRATO,
        MENU_BALANCE_BOLETO_SALVAR
    ]
    message['title'] = 'Adição manual de boletos'

    associados = tbAssociados.objects.filter(
            comissao=request.comissao,
            situacao="ativo",  # Filtra apenas associados ativos
            ).order_by('nome_responsavel')
    
    mensalidade = 0.0
    mensagem = ''

    config = tbComissao.objects.filter(id=request.comissao).first()  # Pega a configuração da comissão atual
    dia_vencimento = config.dia_vencimento if config and config.dia_vencimento else 10
    dt_vencimento = datetime.now().date().replace(day=dia_vencimento)
    if dt_vencimento < datetime.now().date():
        # Se o dia de vencimento já passou este mês, define para o próximo mês
        if dt_vencimento.month == 12:
            dt_vencimento = dt_vencimento.replace(year=dt_vencimento.year + 1, month=1)
        else:
            dt_vencimento = dt_vencimento.replace(month=dt_vencimento.month + 1)

    tp_boleto = config.tipo_boleto.tipo if config and config.tipo_boleto else 'mensal'
    valor_tx_boleto = config.valor_taxa_boleto if config and config.valor_taxa_boleto else 0.0
    incluir_tx_boleto = config.incluir_tx_boleto if config else False

    mensalidade = config.valor_mensalidade if config and config.valor_mensalidade else 0.0
    mensalidade_reajuste = config.valor_mensalidade_reajuste if config and config.valor_mensalidade_reajuste else 0.0
    mensalidade_atual = mensalidade_reajuste if mensalidade_reajuste > mensalidade else mensalidade
    
    if incluir_tx_boleto:
        mensalidade_atual += valor_tx_boleto
        mensagem += f'Incluída taxa de boleto no valor de R$ {valor_tx_boleto:.2f}.'

    config = {
        'dia_vencimento': dia_vencimento,
        'valor_taxa_boleto': valor_tx_boleto,
        'incluir_tx_boleto': incluir_tx_boleto,
        'valor_boleto': mensalidade_atual
    }
    
    # Cria dict com associados e seus códigos
    tabela_associados = { str(associado.id): {'codigo': associado.codigo_associado, 'nome':associado.nome_responsavel} for associado in associados }
    editable_columns = {0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9}  # Índices das colunas editáveis (0-based)
    
    lista_boletos = [{
                'data': f'{datetime.now().date():%d/%m/%Y}',  # Data atual formatada como dd/mm/yyyy,
                'documento': '',
                'nosso_numero': '',
                'associado': '',
                'valor_boleto': f'{mensalidade_atual:.2f}'.replace('.', ','),  # Valor do boleto formatado com duas casas decimais
                'dt_vencimento': f'{dt_vencimento:%d/%m/%Y}',
                'valor_pago': '',
                'dt_pagamento': '',
                'mensagem': mensagem,  # Mensagem do boleto
                'situacao': 'novo',  # Status do boleto
            }]

    df_boletos = pd.DataFrame(lista_boletos)

    context = {
        'menu_options': menu_options,
        'message': message,
        'boletos': df_boletos,
        'tabela_associados': tabela_associados,
        'config': config,
        'editable_columns': editable_columns,
    }

    return render(request, 'boleto_manual.html', context)
    
@user_passes_test(is_sys_admin)
def boleto_view(request):
    """
        Cria e faz gestão de boletos de mensalidades
    """
    message = {'type': 'info', 'text': '', 'title': 'Boleto', 'function': ''}
    is_data_empty = True
    
    # Cria side menu
    menu_options = [
        MENU_VOLTAR,
        MENU_BALANCE_EXTRATO,
        MENU_BALANCE_BOLETO_ADICIONAR, 
        MENU_BALANCE_BOLETO_MANUAL,
        MENU_BALANCE_BOLETO_IMPORTAR, 
        MENU_BALANCE_BOLETO_SALVAR, 
    ]

    lista_boletos = []

    
    # ///////////////// MOSTRA BOLETOS ABERTOS /////////////////
    message['title'] = 'Boletos criados'
    # lê os boletos da comissão com status = 1:novo, 2: aberto e 3: atrasado
    boletos = tbBoleto.objects.filter(
            comissao_id=request.comissao,
            boleto_status__status__in=['novo', 'aberto', 'atrasado', 'pago', 'importado']
        ).order_by('id')
    
    # Verifica se existem boletos abertos
    if boletos.exists():
        # Converte o queryset em uma lista de dicionários
        for boleto in boletos:
            lista_boletos.append({
                'data': f'{boleto.data:%d/%m/%Y}',  # Data atual formatada como dd/mm/yyyy
                'documento': boleto.documento if boleto.documento else '',  # Documento do boleto
                'nosso_numero': boleto.nosso_numero.strip() if boleto.nosso_numero else '',
                'associado': str(boleto.associado.nome_responsavel) if boleto.associado else '',
                'valor_boleto': f'{boleto.valor_boleto:.2f}'.replace('.', ',') if boleto.valor_boleto else '',  # Valor do boleto formatado com duas casas decimais
                'dt_vencimento': f'{boleto.dt_vencimento:%d/%m/%Y}',  # Data de vencimento formatada
                'valor_pago': f'{boleto.valor_pg:.2f}'.replace('.', ',') if boleto.valor_pg else '',
                'dt_pagamento': boleto.dt_pagamento.strftime('%d/%m/%Y') if boleto.dt_pagamento else '',
                'mensagem': boleto.mensagem if boleto.mensagem else '',
                'situacao': boleto.boleto_status.status if boleto.boleto_status else 'desconhecido',  # Status do boleto
            })

    if request.method == 'POST':
        # ///////////////// ADICIONA NOVOS BOLETO EM LOTE /////////////////
        if request.POST.get('novo_boleto', ''):
            message['title'] = 'Preparar novos boletos a serem adicionados'
            mensalidade = 0.0
            mensagem = ''

            config = tbComissao.objects.filter(id=request.comissao).first()  # Pega a configuração da comissão atual
            dia_vencimento = config.dia_vencimento if config and config.dia_vencimento else 10
            dt_vencimento = datetime.now().date().replace(day=dia_vencimento)
            tp_boleto = config.tipo_boleto.tipo if config and config.tipo_boleto else 'mensal'
            valor_tx_boleto = config.valor_taxa_boleto if config and config.valor_taxa_boleto else 0.0
            incluir_tx_boleto = config.incluir_tx_boleto if config else False
            
            mensalidade = config.valor_mensalidade if config and config.valor_mensalidade else 0.0
            mensalidade_reajuste = config.valor_mensalidade_reajuste if config and config.valor_mensalidade_reajuste else 0.0
            mensalidade_atual = mensalidade_reajuste if mensalidade_reajuste > mensalidade else mensalidade
            
            if tp_boleto == 'mensal':
                # Gera boletos para todos os associados mensalmente
                resumo_associado = tbAssociados.objects.filter(
                    comissao=request.comissao,
                    situacao="ativo",  # Filtra apenas associados ativos
                    ).order_by('id')

            else:
                # Gera boletos para associados somento se estiver com mais de 20% do valor da mensalidade em aberto
                mensalidade20 = mensalidade * 0.2  # 20% do valor da mensalidade
                resumo_associado = tbAssociados.objects.filter(
                    comissao=request.comissao,
                    situacao="ativo",  # Filtra apenas associados ativos
                    resumo_associado__valor_em_aberto__gt=mensalidade20
                        ).annotate(
                            valor_em_aberto=Subquery(
                                tbAssociados.objects.filter(id=OuterRef('id')).values('resumo_associado__valor_em_aberto')[:1]
                            )
                        ).order_by('id')
                mensalidade_atual = mensalidade  # Usa o valor anterior da mensalidade
            
            if incluir_tx_boleto:
                mensalidade_atual += valor_tx_boleto
                mensagem += f'Incluída taxa de boleto no valor de R$ {valor_tx_boleto:.2f}.'	

            # -------------cria registro de boleto     
            if resumo_associado.exists():
                # Cria um novo boleto para cada associado com pagamento em aberto
                for associado in resumo_associado:
                    lista_boletos.append({
                        'data': f'{datetime.now().date():%d/%m/%Y}',  # Data atual formatada como dd/mm/yyyy,
                        'documento': associado.codigo_associado,
                        'nosso_numero': '',
                        'associado': associado,
                        'valor_boleto': f'{mensalidade_atual:.2f}'.replace('.', ','),  # Valor do boleto formatado com duas casas decimais
                        'dt_vencimento': f'{dt_vencimento:%d/%m/%Y}',
                        'valor_pago': '',
                        'dt_pagamento': '',
                        'mensagem': mensagem,  # Mensagem do boleto
                        'situacao': 'novo',  # Status do boleto
                    })
                
                #     message['text'] = f'Foram criados {resumo_associado.count()} boletos para associados com pagamento em aberto.'
                #     message['type'] = MESSAGE_TYPE_INFO
                
            else:
                message['text'] = 'Não existem boletos para serem gerados.'
                message['type'] = MESSAGE_TYPE_WARNING

         # ///////////////// IMPORTAR BOLETOS DE ARQUIVO /////////////////
        elif request.POST.get('importar_boleto', ''):
            message['title'] = 'Importa boletos de arquivo'
            file = 'media/2507_boletos.xls'

            df, error = import_boletos_xls(file)

            if error:
                message['text'] = error
                message['type'] = MESSAGE_TYPE_ERROR

            else:
                # Gera lista de boletos existentes no db
                documento_list = {}
                for id, boleto in enumerate(lista_boletos):
                    if boleto['documento'] not in documento_list:
                        documento_list[boleto['documento']] = []
                    documento_list[boleto['documento']].append(id)

                # documento_list = { boleto['documento']:id for id, boleto in enumerate(lista_boletos)  }

                # print(lista_boletos)
                # print(documento_list)
                for boleto_ in df.itertuples(index=False):
                    # Verifica se o boleto já existe no banco de dados
                    documento = boleto_.documento if boleto_.documento else ''
                    documento = str(int(documento)) if type(documento) == float else documento  # Converte para inteiro se for um número válido
                    print(type(documento), f'{20*'/'}')

                    document_exist = False
                    if documento in documento_list:
                        # Procura por boletos com o mesmo documento, vencimento e valor
                        for idx in documento_list[documento]:
                            existing_boleto = lista_boletos[idx]
                            if existing_boleto['dt_vencimento'] == f'{boleto_.vencimento:%d/%m/%Y}' and \
                                existing_boleto['valor_boleto'] == f'{boleto_.valor_boleto:.2f}'.replace('.', ','):
                                document_exist = True

                                # Se o documento já existe, atualiza os campos necessários
                                boleto_existente = lista_boletos[documento_list[documento][idx]]
                                boleto_existente['nosso_numero'] = boleto_.nosso_numero if boleto_.nosso_numero else ''  # Atualiza nosso número
                                boleto_existente['dt_vencimento'] = f'{boleto_.vencimento:%d/%m/%Y}'  # Atualiza data de vencimento
                                boleto_existente['valor_boleto'] = f'{boleto_.valor_boleto:.2f}'.replace('.', ',') if boleto_.valor_boleto else ''  # Atualiza valor do boleto  
                                boleto_existente['dt_pagamento'] = boleto_.dt_pagamento.strftime('%d/%m/%Y') if boleto_.dt_pagamento else ''  # Atualiza data de pagamento
                                boleto_existente['valor_pago'] = f'{boleto_.valor_pago:.2f}'.replace('.', ',') if boleto_.valor_pago else ''  # Atualiza valor pago
                                boleto_existente['situacao'] = 'pago' if boleto_existente['valor_pago'] else boleto_existente['situacao']  # Atualiza status do boleto
                                 # Remove o indice do documento da lista para evitar duplicatas
                                documento_list[documento].pop(idx) 
                                if not documento_list[documento]:
                                    documento_list.pop(documento)
                                break

                    if not document_exist:
                        lista_boletos.append({
                            'data': f'{boleto_.dt_prev_credito:%d/%m/%Y}',  # Data atual formatada como dd/mm/yyyy,
                            'documento': documento,  # Documento do boleto
                            'nosso_numero': boleto_.nosso_numero if boleto_.nosso_numero else '',  # Nosso número do boleto
                            'associado': boleto_.associado.strip().title() if boleto_.associado else '',  # Nome do associado
                            'valor_boleto': f'{boleto_.valor_boleto:.2f}'.replace('.',',') if boleto_.valor_boleto else '',  # Valor do boleto
                            'dt_vencimento': f'{boleto_.vencimento:%d/%m/%Y}',
                            'valor_pago': f'{boleto_.valor_pago:.2f}'.replace('.',',') if boleto_.valor_pago else '',  # Valor pago do boleto
                            'dt_pagamento': boleto_.dt_pagamento.strftime('%d/%m/%Y') if boleto_.dt_pagamento else '',  # Data de pagamento formatada
                            'mensagem': '',  # Mensagem do boleto
                            'situacao': 'importado',  # Status do boleto
                        })

        # ///////////////// SALVAR BOLETOS CRIADOS OU MODIFICADOS /////////////////
        elif request.POST.get('salvar_boleto', ''):
            # Salvar boletos no banco de dados
            lista_boletos = json.loads(request.session['lista_boletos'])    # Recupera boletos da sessão

            linhas_ignoradas = request.POST.get('linhasIgnoradas') # IDs ignorados
            if linhas_ignoradas:
                linhas_ignoradas = json.loads(linhas_ignoradas)
            else:
                linhas_ignoradas = []

            linhas_canceladas = request.POST.get('linhasCanceladas') # IDs cancelados
            if linhas_canceladas:
                linhas_canceladas = json.loads(linhas_canceladas)
            else:
                linhas_canceladas = []

            linhas_modificadas = request.POST.get('linhasModificadas') # IDs modificados
            if linhas_modificadas:
                linhas_modificadas = json.loads(linhas_modificadas)
            else:
                linhas_modificadas = []

            linhas_modificadas = {linha['id']:linha for linha in linhas_modificadas}

            count_add = 0
            count_ignored = 0
            count_updated = 0
            count_canceled = 0

            if lista_boletos:
                log_criacao = save_log(request,
                    description='tBboleto',
                    evento_log_id=12  # log: Criação de boleto
                )
                
                for indice, boleto in enumerate(lista_boletos):
                    # Verifica se a linha do boleto foi ignorada
                    if (indice + 1) in linhas_ignoradas:
                        count_ignored += 1
                        continue
                    
                    # Verifica se o boleto já existe
                    existing_boleto =  tbBoleto.objects.filter(
                        comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
                        documento=boleto['documento'],
                        dt_vencimento=convert_date(boleto['dt_vencimento']),
                        boleto_status__status__in=['novo', 'aberto', 'atrasado', 'pago', 'importado'],
                        # valor_boleto=float(boleto['valor_boleto'].replace(',', '.'))
                    ).first()
                    
                    ''' existing_boleto = lista de boletos que já existem no banco de dados
                        lista_boletos.boleto = boletos salvos na sessão anterior, que podem ser do db, importados, ou incluídos, dependendo do status: novo, aberto, atrasado, pago, importado
                        lista_modificados = lista de boletos que foram modificados na tela
                    '''
                    if (indice + 1) in linhas_modificadas:
                        # Se a linha foi modificada, usa os valores atualizados na tela
                        boleto_ = linhas_modificadas[indice + 1]
                        boleto['valor_boleto'] = boleto_['valor_boleto']
                        boleto['dt_vencimento'] = boleto_['dt_vencimento']
                        boleto['mensagem'] = boleto_['mensagem'].strip() 
                        boleto['documento'] = boleto_['documento'].strip()
                        boleto['nosso_numero'] = boleto_['nosso_numero'].strip()

                    valor_boleto = Decimal(boleto['valor_boleto'].replace(',', '.')) if boleto['valor_boleto'] else 0.0
                    valor_pago = Decimal(boleto['valor_pago'].replace(',', '.')) if boleto['valor_pago'] else 0.0
                    dt_vencimento = convert_date(boleto['dt_vencimento'])
                    dt_pagamento = convert_date(boleto['dt_pagamento']) if boleto['dt_pagamento'] else None
                    mensagem = boleto['mensagem'] if boleto['mensagem'] else ''
                    documento = boleto['documento'].strip() if boleto['documento'] else ''
                    nosso_numero = boleto['nosso_numero'].strip() if boleto['nosso_numero'] else ''

                    associado_instance = tbAssociados.objects.filter(nome_responsavel=boleto['associado']).first()
                    status = 'pago' if valor_pago > 0 else 'cancelado' if (indice + 1) in linhas_canceladas else 'aberto'
                    status_instance = lstBoletoStatus.objects.filter(status=status).first()  # Status 2: aberto 
                    boleto['situacao'] = status

                    if existing_boleto:
                        # Boleto já existe no db

                        if (indice + 1) in linhas_canceladas:
                            # Cancela boleto no db
                            count_canceled += 1
                            existing_boleto.boleto_status = status_instance
                            existing_boleto.save()
                            continue

                        else:
                            # print(f"{existing_boleto.documento.strip()} == {boleto['documento'].strip()}\n{existing_boleto.nosso_numero.strip()} == {boleto['nosso_numero'].strip()}\n{existing_boleto.valor_boleto} == {valor_boleto}\n{existing_boleto.dt_vencimento} == {dt_vencimento}\n{existing_boleto.valor_pg} == {valor_pago}\n{existing_boleto.dt_pagamento} == {dt_pagamento}\n{existing_boleto.mensagem.strip()} == {boleto['mensagem'].strip()}")
                            if existing_boleto.documento.strip() == documento and \
                                 existing_boleto.nosso_numero.strip() == nosso_numero and \
                                    existing_boleto.valor_boleto == valor_boleto and \
                                        existing_boleto.dt_vencimento == dt_vencimento and \
                                            existing_boleto.valor_pg == valor_pago and \
                                                existing_boleto.dt_pagamento == dt_pagamento and \
                                                    existing_boleto.mensagem.strip() == boleto['mensagem'].strip():
                                
                                # Nenhuma alteração necessária no db
                                continue  # Nenhuma alteração necessária, pula para o próximo boleto


                            # Atualiza o boleto existente no db
                            count_updated += 1

                            existing_boleto.documento = documento
                            existing_boleto.nosso_numero = nosso_numero
                            existing_boleto.valor_boleto = valor_boleto
                            existing_boleto.dt_vencimento = dt_vencimento
                            existing_boleto.valor_pg = valor_pago
                            existing_boleto.dt_pagamento = dt_pagamento 
                            existing_boleto.mensagem = mensagem
                            existing_boleto.boleto_status.status = status_instance
                            existing_boleto.save()


                    else:
                        # Cria um novo registro de boleto no db
                        associado_instance = tbAssociados.objects.filter(nome_responsavel=boleto['associado']).first()
                        status = 'pago' if valor_pago else 'aberto'
                        status_instance = lstBoletoStatus.objects.filter(status=status).first()  # Status 2: aberto 
                        tbBoleto.objects.create(
                            comissao_id = request.comissao,
                            data = convert_date(boleto['data']),
                            documento = documento,
                            nosso_numero = nosso_numero,
                            associado = associado_instance,
                            valor_boleto = valor_boleto,
                            dt_vencimento = dt_vencimento,
                            valor_pg = valor_pago,
                            dt_pagamento = dt_pagamento,
                            mensagem = mensagem,
                            boleto_status = status_instance,
                            log_criacao_id = log_criacao
                        )

                        count_add += 1

                if count_add > 0:
                    message['text'] = f'Foram criados {count_add} boletos novos.'

                if count_ignored > 0:
                    message['text'] += f'\nForam ignorados {count_ignored} boletos selecionados.'

                if count_updated > 0:
                    message['text'] += f'\nForam atualizados {count_updated} boletos.'
                
                if count_canceled > 0:
                    message['text'] += f'\nForam cancelados {count_canceled} boletos.'
                
                if message['text'] == '':
                    message['text'] = 'Nenhum boleto foi criado, atualizado ou cancelado.'

                message['type'] = MESSAGE_TYPE_INFO

                # remove da lista boletos com status ['cancelado', 'novo', 'importado']
                remove_boleto = [boleto for boleto in lista_boletos if boleto['situacao'] in ['cancelado', 'novo', 'importado']]
                for boleto in remove_boleto:
                    lista_boletos.remove(boleto)

        # ///////////////// SALVAR BOLETOS CRIADOS MANUALMENTE /////////////////
        elif request.POST.get('salvar_boleto_manual'):
            count_add = 0
            count_ignored = 0
            boletos = request.POST.dict()  # Recupera os dados como um dicionário
            boletos = {key: value for key, value in boletos.items() if key.startswith('boletos')}
            boleto_list_ = []
            for key, value in boletos.items():
                # Extrai o índice e o campo do nome do input
                valores = re.findall(r'\[([^\[\]]+)\]', key)
                index = int(valores[0]) if valores[0].isdigit() else -1  # Índice do boleto na lista
                if index >= 0:
                    field = valores[1].strip()  # Nome do campo (data, documento, etc.)
                    value = value.strip()  # Remove espaços em branco extras
                    if len(boleto_list_) <= (index):
                        boleto_list_.append({})

                    boleto_list_[index][field] = value

            for boleto in boleto_list_:
                # Adiciona o valor ao dicionário do boleto correspondente
                valor_boleto = Decimal(boleto.get('valor_boleto').replace(',', '.')) if boleto.get('valor_boleto') else 0.0
                valor_pago = Decimal(boleto.get('valor_pago').replace(',', '.')) if boleto.get('valor_pago') else 0.0
                associado_instance = tbAssociados.objects.filter(nome_responsavel=boleto['associado']).first()
                status = 'pago' if valor_pago > 0 else 'aberto'
                status_instance = lstBoletoStatus.objects.filter(status=status).first()  # Status 2: aberto 
                dt_vencimento = convert_date(boleto['dt_vencimento'])
                dt_pagamento = convert_date(boleto['dt_pagamento']) if boleto['dt_pagamento'] else None
                boleto['situacao'] = status

                # Verifica se o boleto já existe
                existing_boleto =  tbBoleto.objects.filter(
                    comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
                    documento=boleto['documento'],
                    boleto_status__status__in=['novo', 'aberto', 'atrasado', 'pago', 'importado'],
                    dt_vencimento=dt_vencimento,
                    valor_boleto=valor_boleto
                ).first()

                if existing_boleto:
                    count_ignored += 1
                    pass

                else:
                    lista_boletos.append({
                                    'data': boleto['data'], 
                                    'documento': boleto['documento'], 
                                    'nosso_numero': boleto['nosso_numero'], 
                                    'associado': boleto['associado'], 
                                    'valor_boleto': boleto['valor_boleto'],  
                                    'dt_vencimento': boleto['dt_vencimento'],  
                                    'valor_pago': boleto['valor_pago'],
                                    'dt_pagamento':boleto['dt_pagamento'],
                                    'mensagem': boleto['mensagem'].strip(),  
                                    'situacao': status  
                                })
                    count_add += 1
                    
                    log_criacao = save_log(request,
                        description='tBboleto',
                        evento_log_id=12  # log: Criação de boleto
                        )

                    tbBoleto.objects.create(
                                comissao_id = request.comissao,
                                data = convert_date(boleto['data']),
                                documento = boleto['documento'] if boleto['documento'] else '',
                                nosso_numero = boleto['nosso_numero'] if boleto['nosso_numero'] else '',
                                associado = associado_instance,
                                valor_boleto = valor_boleto,
                                dt_vencimento = dt_vencimento,
                                valor_pg = valor_pago,
                                dt_pagamento = dt_pagamento,
                                mensagem = boleto['mensagem'],
                                boleto_status = status_instance,
                                log_criacao_id = log_criacao
                            )
            
            message['text'] = f'Foram criados {count_add} boletos novos.'
            if count_ignored > 0:
                message['text'] += f'\nForam ignorados {count_ignored} boletos que já existem.'

    df_boletos = pd.DataFrame(lista_boletos)
    is_data_empty = False if not df_boletos.empty else True
    if not is_data_empty:
        df_boletos['associado'] = df_boletos['associado'].astype(str)  # Converte a coluna 'associado' para string
    
        # Ordena por 'associado'
        df_boletos = df_boletos.fillna('')  # Preenche valores NaN com string vazia
        df_boletos.sort_values(by='associado', inplace=True, key=lambda x: x.str.lower() )  # Ordena por associado (nome) em ordem alfabética
        df_boletos.reset_index(drop=True, inplace=True)  # Reseta o índice do DataFrame
        
        # Serializar o DataFrame para JSON e armazená-lo na sessão
        request.session['lista_boletos'] = df_boletos.to_json(orient='records')  # Armazena o DataFrame na sessão

    context = {
        'menu_options': menu_options,
        'message': message,
        'boletos': df_boletos,
        'is_data_empty': is_data_empty,
    }

    return render(request, 'boleto.html', context)

@user_passes_test(is_sys_admin)
def analise_movimentacao_view(request):
    """
        Analisa as movimentações financeiras do extrato bancário
    """

    message = {'type': 'info', 'text': '', 'title': 'Analisar e classificar movimentação', 'function': ''}
    status = None

    # Cria side menu
    menu_options = [
        MENU_VOLTAR,
        MENU_BALANCE_EXTRATO,
        MENU_BALANCE_ANALISAR_MOVIMENTACAO,
        MENU_BALANCE_SALVAR_MOVIMENTACOES,
        MENU_BALANCE_REVISAR_ANALISE
        ]

    # metodo post
    if request.method == 'POST':

        if request.POST.get('review', ''):
            # Revisar movimentação
            status = 1  
            message['title'] = 'Revisar e incorporar movimentação'

            menu_options.append(MENU_BALANCE_FECHAR_ANALISE)

        elif request.POST.get('close', ''):
            # Fechar análise: confirmação
            status = 1 
            message['title'] = 'Fechar análise'

            menu_options.append(MENU_BALANCE_FECHAR_ANALISE)

            count_close = tbExtrato.objects.filter(
                comissao_id=request.comissao if request.comissao else 1,  
                status = 1  # Status 1: registros associados
            ).count()

            count_out = tbExtrato.objects.filter(
                comissao_id=request.comissao if request.comissao else 1,    
                status__isnull = True
            ).count()

            if count_close > 0:
                reg_closed =  f'Existem {count_close} registros de movimentação que serão incorporado à contabilidade.\n\n'
                reg_out = ''
                if count_out > 0:
                    reg_out =     f'Existem {count_out} registros de movimentação que não foram associados e serão apagados.\n\n'
                                    
                message['text'] = f'{reg_closed}{reg_out}Tem certeza que deseja fechar a análise de movimentação?\n\
                    Essa operação não poderá ser revertida'
                message['type'] = MESSAGE_TYPE_CONFIRM
                message['function'] = 'submitForm("formConfirmarFechamento")'  # Função JS para confirmar fechamento

            else:
            
                message['text'] = 'Não há movimentações associadas para fechar a análise.'

        elif request.POST.get('confirm_close', ''): 
            # Fechar análise
            status = 2
            message['title'] = 'Concluir análise e incorporar movimentações'
            # cria log
            log_id = save_log(request,
                description='tbExtrato',
                evento_log_id=11  # log: Fechamento de movimentação
            )

        else:
            # Fazer associações
            ignorados = request.POST.get('ignorados', '').split(',')  # IDs ignorados
            ignorados = [ int(id.strip()) for id in ignorados if id.strip().isdigit() ]  # Converte para inteiros e remove vazios
            ids_duplicados = eval('{' + request.POST.get('ids_duplicados', '') + '}')
            valores_atualizados = list(ids_duplicados.values())

            # cria log
            log_id = save_log(request,
                description='tbExtrato',
                evento_log_id=10  # log: Análise de movimentação
            )

            count_duplicados = 0
            count_associados = 0

            # Salva modificações
            for extrato_id in request.POST.getlist('extrato_id'):
                updated = False  # Flag para verificar se o extrato foi atualizado
                extrato_id = int(extrato_id)

                if extrato_id in ignorados:
                    # exclui registro ignorado
                    continue
                
                # Duplica movimentação
                if extrato_id in ids_duplicados.keys():
                    # recupera o registro original
                    id_original = ids_duplicados[extrato_id]
                    extrato_original = tbExtrato.objects.get(id=id_original)

                    # duplica registro
                    extrato = tbExtrato.objects.create(
                        comissao_id=extrato_original.comissao_id,
                        data=extrato_original.data,
                        documento=f'duplicado: {extrato_original.documento}',
                        historico=extrato_original.historico,
                        tipo=extrato_original.tipo,
                        nome=extrato_original.nome,
                        nota=extrato_original.nota,
                        cpf=extrato_original.cpf,
                        log_registro_id=extrato_original.log_registro_id,  
                    )

                    # recupera id do novo registro
                    novo_id = extrato.id

                    # atualiza dicionario de ids_duplicados
                    for id in ids_duplicados.keys():
                        if ids_duplicados[id] == extrato_id:
                            ids_duplicados[id] = novo_id
                    
                    # Remove o ID original da lista de valores atualizados
                    if extrato_id in valores_atualizados:
                        valores_atualizados.pop(valores_atualizados.index(extrato_id))  

                    # Adiciona o novo ID à lista de valores atualizados
                    count_duplicados += 1
                    updated = True
                    valores_atualizados.append(novo_id)  
                
                else:
                    # Atualiza o registro existente
                    extrato = tbExtrato.objects.get(id=extrato_id)
                    
                # Atualizar os campos modificados
                id_transacao = f'transacao_tipo_{extrato_id}'

                transacao_id = request.POST.get(id_transacao, extrato.transacao_id)
                if transacao_id and transacao_id.isdigit():
                    transacao_id = int(transacao_id)  # Converte para inteiro se for um ID válido
                else:
                    transacao_id = None
                
                # Atualizar associado_id apenas para transações com "mensalidade" no texto
                if transacao_id:
                    transacao = tbTransacao.objects.get(id=transacao_id)
                else:
                    continue  # Pula transações não definida
                
                if transacao.value == '***':
                    continue  # Pula transações não conhecidas
                
                if extrato.transacao_id != transacao_id:
                    extrato.transacao_id = transacao_id
                    updated = True  # Marca como atualizado

                if "mensalidade" in transacao.key.lower():
                    associado_id = request.POST.get(f'associado_codigo_{extrato_id}')
                    if associado_id and associado_id.isdigit():
                        associado_id = int(associado_id)  # Converte para inteiro se for um ID válido
                    else:
                        associado_id = None

                    if associado_id:
                        if extrato.associado_id != associado_id:
                            extrato.associado_id = associado_id
                            updated = True
                    else:
                        continue  # Pula associado não definido

                # Atualizar os valores de crédito e débito se estiverem na lista de duplicados
                if extrato_id in valores_atualizados:
                    updated = True
                    credito = request.POST.get(f'credito_{extrato_id}', None)
                    if credito and credito.strip():  # Verifica se o valor não é vazio ou None
                        extrato.credito = Decimal(credito.replace(',', '.'))  # Converte para número após substituir vírgula por ponto
                    else:
                        extrato.credito = None  # Define como None se o valor for inválido
                    
                    debito = request.POST.get(f'debito_{extrato_id}', None)
                    if debito and debito.strip():  # Verifica se o valor não é vazio ou None
                        extrato.debito = Decimal(debito.replace(',', '.'))  # Converte para número após substituir vírgula por ponto
                    else:
                        extrato.debito = None  # Define como None se o valor for inválido

                # Atualizar log_associacao_id
                extrato.log_associacao_id = log_id
                
                # Atualiza status do extrato para 1: associadao
                extrato.status = 1
                
                # Salva
                if updated:
                    extrato.save()
                    count_associados += 1

            # return redirect('analise_movimentacao')  # Redireciona para a mesma página após o POST
            if count_associados > 0:
                text_message = f'Foram atualizados {count_associados} registros de extrato.'
                if count_duplicados > 0:
                    text_message += f'\nForam duplicados {count_duplicados} registros de extrato.'
            else:
                text_message = 'Nenhum registro de extrato foi atualizado.'
            message['text'] = text_message
    
    if status == None:
        # lê tabela tbExtrato onde comissao == comissao atual e log_associacao_id == null para analisar movimentação
        extratos = tbExtrato.objects.filter(
            comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id   
            status__isnull=True,
        ).order_by('id')

    elif status == 2:   # Fechar análise
        num_updated = tbExtrato.objects.filter(
            comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
            status = 1
        ).update(status=2, log_fechamento_id=log_id)  # Atualiza status para 2: fechado
        
        num_deleted = tbExtrato.objects.filter(
            comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
            log_associacao_id__isnull=True,
        ).update(status=0, log_fechamento_id=log_id)  # Atualiza status para 0: deletado

        text_updated = f'Foram incorporados {num_updated} registros de movimentação ao banco de dados da contabilidade.'
        if num_deleted > 0:
            text_updated += f'\nForam apagados {num_deleted} registros de movimentação que não foram associados.'
        
        message['text'] = text_updated
        status = 1
        
    if status == 1:
        # lê tabela tbExtrato onde comissao == comissao atual e log_associacao_id != null para revisar movimentação
        extratos = tbExtrato.objects.filter(
            comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id   
            status=1  # Status 1: registros associados
        ).order_by('id')
    
    # Lê tabela tbTransacao para preencher os tipos de transação
    transacoes = tbTransacao.objects.all().order_by('key')

    # Cria um dicionário para mapear transacao_id para color_value
    transacao_colors = {transacao.id: transacao.color_name for transacao in transacoes}

    # Cores para JS no frontend
    colors_string_json = [ f'"{transacao.id}": "{transacao.color_name}"' for transacao in transacoes]

    comissao = request.comissao if request.comissao else 1  # Valor padrão para comissao_id
    
    extratos_list = []
    for index, extrato in enumerate(extratos):
        if extrato.transacao_id:
            tipo_transacao = {'id': extrato.transacao_id, 'configuracao': '', 'user': extrato.associado_id}  # Transação já associada ao extrato
        else:
            tipo_transacao = identify_transaction(comissao, extrato.historico, extrato.credito)

        cor = transacao_colors.get(tipo_transacao['id'], '#FFFFFF')  # Cor padrão: branco
        extratos_list.append({
            'indice': index + 1,  # Índice começa em 1
            'id': extrato.id,
            'data': extrato.data.strftime('%d/%m/%Y') if extrato.data else None,
            'historico': extrato.historico,
            'credito': extrato.credito or '',
            'debito': extrato.debito or '',
            'transacao_id': tipo_transacao['id'],   # código da transação associada ao extrato
            'associado_id': tipo_transacao['user'] if tipo_transacao['user'] else None,
            'cor': cor  # Adiciona a cor ao contexto,
        })

    # Lê tabela tbAssociado para preencher os códigos de pagamento (filtrando por comissão atual)
    associados = tbAssociados.objects.filter(
        comissao=request.comissao,  # Filtrar por comissão atual
    ).order_by('id')
    
    
    is_data_empty = True if not extratos_list else False

    colors_string_json = '{' + ', '.join(colors_string_json) + '}'
    context = {
        'menu_options': menu_options,
        'extratos_list': extratos_list,
        'transacoes': transacoes,
        'associados': associados,
        'cor_transacao': colors_string_json,
        'is_data_empty': is_data_empty,
        'message': message,
    }
    return render(request, 'analise_movimentacao.html', context)

@user_passes_test(is_sys_admin)
def get_extrato_details(request, extrato_id):
    """
        Retorna os detalhes de um extrato específico em formato JSON.
    """
    
    extrato = get_object_or_404(tbExtrato, id=extrato_id)
    comissao = request.comissao
    codigo_pagamento = ''

    if extrato.nome:
        user = get_user_by_responsible_name(comissao, extrato.nome)
        if user:
            codigo_pagamento = user.codigo_pagamento

    data = {
        'id': extrato.id,
        'data': extrato.data.strftime('%d/%m/%Y') if extrato.data else '',
        'historico': extrato.historico,
        'credito': extrato.credito or '',
        'debito': extrato.debito or '',
        'nome': extrato.nome or '',
        'cpf': extrato.cpf or '',
        'nota': extrato.nota or '',
        'codigo_pagamento': codigo_pagamento,
    }

    return JsonResponse(data)


@user_passes_test(is_sys_admin)
def edit_extrato_view(request):
    if request.method == 'POST':
        extrato_id = request.POST.get('extrato_id')
        extrato = get_object_or_404(tbExtrato, id=extrato_id)

        if request.method == 'POST':
            extrato.data = request.POST.get('date')
            extrato.documento = request.POST.get('doc')
            extrato.historico = request.POST.get('description')
            extrato.valor_credito = request.POST.get('credit')
            extrato.valor_debito = request.POST.get('debit')
            extrato.anotacao = request.POST.get('note')
            extrato.save()
            return redirect('transaction')

        return render(request, 'edit_extrato.html', {'extrato': extrato})
    else:
        return redirect('transaction')  # Redireciona para balance se não for POST


@user_passes_test(is_sys_admin)
def entrada_manual_view(request):
    """
        Cria uma entrada manual de movimentação financeira para compor o livro caixa adicionalmente ao extrato bancário
    """
    transacoes = tbTransacao.objects.all().order_by('key')
    data_atual = datetime.now().strftime('%d/%m/%Y')  # Formata a data atual como dd/mm/yyyy
    error = ''
    message = ''
    sucesso = False

    # Cria side menu
    menu_options = [  
        MENU_VOLTAR,
        MENU_BALANCE_EXTRATO,
    ]

    if request.method == 'POST':
        # Obtém os dados do formulário POST
        valor = ''
        data = request.POST.get('data', '').strip()
        documento = 'entrada manual'  # Valor fixo para documento
        historico = request.POST.get('historico', '').strip()
        credito = request.POST.get('valor') if request.POST.get('tipo') == 'credito' else ''
        debito = request.POST.get('valor') if request.POST.get('tipo') == 'debito' else ''
        nome = request.POST.get('nome', '').strip().upper()  # Converte o nome para maiúsculas
        nota = request.POST.get('nota', '').strip()
        transacao_id = request.POST.get('documento', '').strip()

        # Converte a data para o formato adequado
        data_formatada = convert_date(data)
        
        if data_formatada == '':
            error = 'Data inválida. Por favor, insira uma data válida no formato dd/mm/yyyy.'   
        
        else:
            log_id = save_log(request,
                description='tbExtrato-registro manual',
                evento_log_id=9  # log: Entrada manual de extrato
            )

            # Cria uma nova entrada de extrato
            novo_extrato = tbExtrato(
                comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
                data=data_formatada,
                documento=documento,
                historico=historico,
                credito=Decimal(credito.replace(',', '.')) if credito else None,
                debito=Decimal(debito.replace(',', '.')) if debito else None,
                nome=nome,
                nota=nota,
                transacao_id=transacao_id,
                log_registro_id=log_id,  # Usa o ID do log criado
            )
            
            novo_extrato.save()

            sucesso = True
            message = 'Registro manual salvo com sucesso.'
            # limpa request
            request.POST = None

    context = {
                'menu_options': menu_options,
                'transacoes':   transacoes,
                'data_atual':   data_atual,
                'error':        error,
                'message':      message,
                'sucess':      sucesso
            }

    return render(request, 'entrada_manual.html', context)


@user_passes_test(is_sys_admin)
def transaction_view(request):
    """
        Lê um extrato bancário e o prepara para importação
    """
    dataframe = None
    context = {}
    error = ''
    is_dataframe_empty = True
    file=''
    message = {'type': 'info', 'text': '', 'title': 'Importação de extrato', 'function': ''}
    # obtem nome do banco de dbComissao
    nome_banco = tbComissao.objects.filter(id=request.comissao).first().banco 
    nome_banco = nome_banco if nome_banco else 'SICOOB'
    print('-->', nome_banco)
    # Cria side menu
    menu_options = [MENU_VOLTAR]
    
    # POST request para upload de arquivo Excel
    if request.method == 'POST' and 'file' in request.FILES:
        file = request.FILES['file']            # Nome original do arquivo
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)     # Novo nome para o arquivo, salvo no servidor
        file_path = fs.path(filename)           # Caminho completo do arquivo salvo

        # Extrato SICOOB XLS
        if file_path.endswith('xlsx') or file_path.endswith('xls'):
            dataframe, error = process_sicoob_input_xls(file_path)
            if error:
                message['text'] = error.format(file=file.name)
                message['type'] = MESSAGE_TYPE_ERROR

        # Extrato SICOOB TXT
        elif file_path.endswith('txt'): 
            dataframe, error = process_sicoob_input_txt(file_path)
            if error:
                message['text'] = error.format(file=file.name)
                message['type'] = MESSAGE_TYPE_ERROR
            
        # Apagar o arquivo após o processamento
        if os.path.exists(file_path):  # Verifica se o arquivo existe
            os.remove(file_path)  # Remove o arquivo

        is_dataframe_empty = dataframe.empty if dataframe is not None else True

        if not is_dataframe_empty:
            dataframe = dataframe.fillna('')  # Preenche valores NaN com string vazia
            # Serializar o DataFrame para JSON e armazená-lo na sessão
            request.session['dataframe'] = dataframe.to_json(orient='records')

            context['file_name'] = filename
            context['dataframe'] = dataframe,
            
            # Cria side menu para extrato
            menu_options.extend([
                MENU_BALANCE_EXTRATO,
                MENU_BALANCE_ACEITAR_EXTRATO,
            ])

    else:
        menu_options.extend([
            MENU_BALANCE_IMPORTAR_EXTRATO,
            MENU_BALANCE_ENTRADA_MANUAL,
            MENU_BALANCE_ANALISAR_MOVIMENTACAO,  
            MENU_BALANCE_BOLETO,
        ])
    
    context = {
                'is_dataframe_empty': is_dataframe_empty,
                'menu_options': menu_options,
                'message': message,
                'file_name': file,
                'dataframe': dataframe,
                'nome_banco': nome_banco,
            }
    return render(request, 'transaction.html', context)


@user_passes_test(is_sys_admin)
def extrato_config(request):
    # Consulta os dados da view 'config_extrato'
    extrato_configs = tbExtratoConfig.objects.select_related('popup_config').all()
    return render(request, 'extrato_config.html', {'extrato_configs': extrato_configs})


@user_passes_test(is_sys_admin)
def importacao_view(request):
    """
        Importa um extrato bancário procesando linhas duplicadas e convertendo os dados para um banco de dados
    """

    titulo = 'Importação de Extrato'
    message = {'type': 'info', 'text': '', 'title': 'Importação de extrato', 'function': ''}
    error = None
    duplicadas = request.session.get('duplicadas', [])
    novas_linhas = request.session.get('novas_linhas', [])
    menu_options = [MENU_VOLTAR]

    # Processa linhas duplicadas se houver
    if request.method == 'POST':
        
        linhas_aceitas = request.POST.get('linhasAceitas', '[]')
        try:
            # Verifica se o valor é um JSON válido
            if linhas_aceitas:
                linhas_aceitas = json.loads(linhas_aceitas)

            if not isinstance(linhas_aceitas, list):  # Garantir que seja uma lista
                linhas_aceitas = []

        except json.JSONDecodeError:
            error = "Erro ao desserializar 'linhasAceitas'"
            duplicadas = None
            novas_linhas = []
            linhas_aceitas = []  # Define como lista vazia em caso de erro

        for linha in linhas_aceitas:
            novas_linhas.append(duplicadas[linha - 1])

        duplicadas = []

    else:
        pass

    if not duplicadas and novas_linhas:
        # Grava os dados do extrato na tabela tbExtrato

        # registra log
        log_id = save_log(request,
            f'tbExtrato: {len(novas_linhas)} novos registros',
            evento_log_id = 8  # log: Novo extrato importado
            )

        novas_linhas_db = []
        for linha in novas_linhas:
            # Converter o formato da data de dd/mm/yyyy para yyyy-mm-dd
            data = convert_date(linha.get('data', None))  # Função utilitária para converter a data

            novas_linhas_db.append(tbExtrato(
            comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
            data=data if data else None,  # Tratar valores vazios
            documento=linha.get('documento', None),
            historico=linha.get('historico', None),
            credito=linha.get('credito', None) if linha.get('credito', None) != '' else None,  # Tratar valores vazios
            debito=linha.get('debito', None) if linha.get('debito', None) != '' else None,
            tipo=linha.get('tipo', None),
            nome=linha.get('nome', None),
            nota=linha.get('nota', None),
            cpf=linha.get('cpf', None),
            saldo=linha.get('saldo', None) if linha.get('saldo', None) != '' else None,
            log_registro_id=log_id
        ))
        
        duplicadas = None
            
        # Verifica se há novas linhas para salvar no banco de dados
        if novas_linhas_db:
            # Salvar as novas linhas no banco de dados
            try:
                tbExtrato.objects.bulk_create(novas_linhas_db)
                message['text'] =  f'Importação completada com sucesso.\nForam adicionados {len(novas_linhas_db)} novos registros de extrato ao bando de dados.'
                message['type'] = MESSAGE_TYPE_SUCCESS
                message['function'] = "loadPage('/transaction/analise-movimentacao')"
            except Exception as e:
                error = f'Erro ao importar: {str(e)}'
        else:
            error = 'Erro ao adicionar registros ao banco de dados.'

        # Limpar variáveis de sessão após o processamento
        request.session.pop('dataframe', None)
        request.session.pop('duplicadas', None)
        request.session.pop('novas_linhas', None)
    
    elif not duplicadas and not error:
        # Se não houver duplicadas e nenhuma nova linha, exibe mensagem
        message['text'] = 'Nenhum registro novo para importar.'
        message['type'] = MESSAGE_TYPE_INFO
        message['function'] = "loadPage('/transaction')"
        duplicadas = None

    if error:
        message['text'] = error
        message['type'] = MESSAGE_TYPE_ERROR

    else:
        # Trata tabelas de extrato duplicadas na sessão
        if novas_linhas:
            message['text'] = f'Foram encontradas {len(novas_linhas)} novas entradas de extrato.\n'
            message['type'] = MESSAGE_TYPE_INFO
        if duplicadas:
            message['text'] += f'Foram encontradas {len(duplicadas)} entradas duplicadas no extrato. Por favor, reveja e aceite ou rejeite as entradas conforme necessário.'
            message['type'] = MESSAGE_TYPE_WARNING

    menu_options.append(MENU_BALANCE_EXTRATO)
    
    if duplicadas:
        menu_options.append(MENU_BALANCE_ACEITAR_ENTRADAS_EXTRATO)
        message['title'] = 'Entradas de extrato duplicadas'

    context = {'duplicadas': duplicadas, 
               'error': error, 
               'message': message,
               'menu_options': menu_options,
               'titulo': titulo,
    }

    return render(request, 'importacao.html', context)
    

@user_passes_test(is_sys_admin)
def aceitar_extrato(request):
    """
        Prepara o extrato para inserir os dados em um banco de dados
    """

    if request.method == 'POST':
        # Recuperar o DataFrame da sessão e desserializá-lo
        dataframe_json = request.session.get('dataframe', None)
        if not dataframe_json:
            return redirect('transaction')  # Redireciona para a página principal se não houver DataFrame

        dataframe = pd.read_json(dataframe_json, orient='records')

        duplicadas = []
        novas_linhas = []

        for _, row in dataframe.iterrows():
            data = convert_date(row['data'])

            # Verificar se a linha já existe no banco de dados
            existe = tbExtrato.objects.filter(
                comissao_id=request.comissao if request.comissao else 1,  # Valor padrão para comissao_id
                data=data,
                documento=row['documento'],
                historico=row['historico'],
                credito=row['credito'] if row['credito'] != '' else None,  # Tratar valores vazios
                debito=row['debito'] if row['debito'] != '' else None  # Tratar valores vazios
            ).exists()

            if existe:
                duplicadas.append(row)
            else:
                novas_linhas.append(row)

        # Redirecionar para a página de importação
        request.session['duplicadas'] = [row.to_dict() for row in duplicadas]
        request.session['novas_linhas'] = [row.to_dict() for row in novas_linhas]

        return redirect('importacao')
    
    else:   # GET request, não faz nada e redireciona para balance
        pass

    return redirect('transaction')