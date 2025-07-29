from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from datetime import datetime
import pandas as pd
import json
import os
from .models import tbExtratoConfig, tbExtrato, tbTransacao
from users.models import tbAssociados
from .utils import process_sicoob_input, convert_date, identify_transaction, save_log, get_user_by_responsible_name
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
                            MENU_BALANCE_FECHAR_ANALISE_CONFIRMAR

# Função para verificar se o usuário pertence ao grupo 'admin'
def is_sys_admin(user):
    is_admin = user.groups.filter(name='sys-admin').exists() or \
                user.groups.filter(name='app-admin').exists() or \
                user.groups.filter(name='master').exists()
    return is_admin


@user_passes_test(is_sys_admin)
def analise_movimentacao_view(request):
    """
        Analisa as movimentações financeiras do extrato bancário
    """

    message = {'type': 'info', 'text': '', 'title': 'Analisar movimentação', 'function': ''}
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
            message['title'] = 'Revisar movimentação'

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
                                    
                message['text'] = f'{reg_closed}{reg_out}Tem certeza que deseja fechar a análise de movimentação?\n \
                                    Essa operação não poderá ser revertida'
                message['type'] = 'confirm'
                message['function'] = 'submitForm("formConfirmarFechamento")'  # Função JS para confirmar fechamento

            else:
            
                message['text'] = 'Não há movimentações associadas para fechar a análise.'

        elif request.POST.get('confirm_close', ''): 
            # Fechar análise
            status = 2
            message['title'] = 'Fechar análise'
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
                    print('duplicado...')
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
                        extrato.credito = float(credito.replace(',', '.'))  # Converte para número após substituir vírgula por ponto
                    else:
                        extrato.credito = None  # Define como None se o valor for inválido
                    
                    debito = request.POST.get(f'debito_{extrato_id}', None)
                    if debito and debito.strip():  # Verifica se o valor não é vazio ou None
                        extrato.debito = float(debito.replace(',', '.'))  # Converte para número após substituir vírgula por ponto
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
        MENU_BALANCE_IMPORTAR_EXTRATO,
        MENU_BALANCE_ENTRADA_MANUAL,
        MENU_BALANCE_ANALISAR_MOVIMENTACAO,
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
                credito=float(credito.replace(',', '.')) if credito else None,
                debito=float(debito.replace(',', '.')) if debito else None,
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
    user_groups = request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    menu_options = []
    dataframe = None

    # Cria side menu
    menu_options = [
        MENU_VOLTAR,
        MENU_BALANCE_IMPORTAR_EXTRATO,
        MENU_BALANCE_ENTRADA_MANUAL,
        MENU_BALANCE_ANALISAR_MOVIMENTACAO,  
    ]
    context = {
                'is_dataframe_empty': True,
                'menu_options': menu_options,
            }
    
    # POST request para upload de arquivo Excel
    if request.method == 'POST' and 'file' in request.FILES:
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            # Ler o arquivo Excel e convertê-lo em um DataFrame
            dataframe = pd.read_excel(file_path)
            is_dataframe_empty = dataframe.empty if dataframe is not None else True
            # print("DataFrame loaded successfully:", dataframe.head(5))  # Debug: Exibe as primeiras linhas do DataFrame
        except Exception as e:
            context['error'] = f'O arquivo não e um Excel válido: "{file}"'
            is_dataframe_empty = True
        finally:
            # Apagar o arquivo após o processamento
            if os.path.exists(file_path):  # Verifica se o arquivo existe
                os.remove(file_path)  # Remove o arquivo
        
        if not is_dataframe_empty:
            # print("DataFrame is not empty, processing...")  # Debug: Confirma que o DataFrame não está vazio
            if 'EXTRATO CONTA CORRENTE' in dataframe.head(0):
                dataframe.drop(1, inplace=True)  # Remove a primeira linha do DataFrame
                dataframe.columns = ['data', 'documento', 'historico', 'credito']
                dataframe = dataframe.fillna('')  # Preenche valores NaN com string vazia
                
                # Processar o DataFrame para reorganizar as linhas adicionais
                dataframe = process_sicoob_input(dataframe)

                # Serializar o DataFrame para JSON e armazená-lo na sessão
                request.session['dataframe'] = dataframe.to_json(orient='records')

                # Cria side menu para extrato
                menu_options = [
                    MENU_VOLTAR,
                    MENU_BALANCE_EXTRATO,
                    MENU_BALANCE_ACEITAR_EXTRATO,
                ]
                                
                context = { 
                    'is_dataframe_empty': False,
                    'menu_options': menu_options,
                    'file_name': file.name,
                    'dataframe': dataframe,
                }
            else:
                context['error'] = f'O arquivo "{file.name}" não contém um extrato do banco Sicoob.'
        

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
    message = None
    error = None
    duplicadas = request.session.get('duplicadas', [])
    novas_linhas = request.session.get('novas_linhas', [])
    menu_options = [MENU_VOLTAR]

    # Processa linhas duplicadas se houver
    if request.method == 'POST':
        
        linhas_aceitas = request.POST.get('linhasAceitas', '[]')
        print("linhas_aceitas", linhas_aceitas)
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
                message =  f'Importação completada com sucesso. Foram adicionados {len(novas_linhas_db)} novos registros de extrato ao bando de dados.'
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
        message = 'Nenhum registro novo para importar.'
        duplicadas = None

    elif not error:
        # Trata tabelas de extrato duplicadas na sessão
        error = f'Foram encontradas {len(duplicadas)} entradas duplicadas no extrato. Por favor, reveja e aceite ou rejeite as entradas conforme necessário.'
        message = f'Foram encontradas {len(novas_linhas)} novas entradas de extrato.'

    menu_options.append(MENU_BALANCE_EXTRATO)
    
    if duplicadas:
        menu_options.append(MENU_BALANCE_ACEITAR_ENTRADAS_EXTRATO)
        titulo = 'Entradas de extrato duplicadas'


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