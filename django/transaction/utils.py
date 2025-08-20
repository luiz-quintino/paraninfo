import pandas as pd
import regex as re
from datetime import datetime
from home.models import tbPagina, tbLog
from users.models import tbAssociados
from transaction.models import tbExtratoConfig, tbTransacao


def save_log(request, description, evento_log_id) -> int:
    # Registra log de evento no banco de dados
    pagina = tbPagina.objects.get(pagina=request.resolver_match.url_name)
    seessao_ativa_id = request.session['user_data']['sessao_id']

    log = tbLog.objects.create(
        pagina_id = pagina.id,
        evento_log_id = evento_log_id,
        sessao_ativa_id = seessao_ativa_id,
        descricao = description,
    )

    return log.id


def get_user_by_codigo_pagamento(comissao: str, codigo_pagamento: int) -> tbAssociados:
    """
        Localiza o usuário pelo código de pagamento.
    """
    user = tbAssociados.objects.filter(comissao=comissao, codigo_pagamento=codigo_pagamento).first()  # retorna o primeiro usuário encontrado ou None

    if user:
        return user
    
    return None

def get_user_by_responsible_name(comissao: str, name: str) -> tbAssociados:
    """
        Localiza o usuário pelo código de pagamento.
    """
    name = name.strip().lower()
    user = tbAssociados.objects.filter(comissao=comissao, nome_responsavel__iexact=name).first()  # retorna o primeiro usuário encontrado ou None

    if user:
        return user
    
    return None

def identify_transaction(comissao: str, description: str, value: float) -> dict:
    """
        Identifica o tipo de transação e/ou o usuário com base na descrição e no valor.
        transaction = {
            'id': <transacao_id>,                   # id da transaçõa
            'configuracao': <configuracao>,         # configuração da transação, se houver
            'user': <user_id>                       # id do usuário se "#find_user
        }
    """

    transaction = {'id': None, 'configuracao': '', 'user': 0}
    description = description.strip()
    # print(f"> Transação: {description}, Valor: {value}")

    config = tbExtratoConfig.objects.filter(descricao__icontains=description).order_by('id').first()
    if config:
        # print(f'   ...{config.descricao}, {config.condicao}, {config.configuracao}, {config.transacao_id}')
        transaction['id'] = config.transacao_id
        # verificar se existe condição 'find_user' senão condição hide
        if config.condicao == '#find_user':
            # localiza usuário pelo identificador dos centavos
            user_id = 0

            if type(value).__name__ == 'Decimal':
                user_id = int((value % 1) * 100)

            if user_id > 0:
                # busca pelo usuário em tbAssociados.codigo_pagamento
                user = get_user_by_codigo_pagamento(comissao, user_id)  # retorna o primeiro usuário encontrado ou None

                if user:
                    transaction['user'] = user.id

                    return transaction
                
                else:
                    transaction['configuracao'] = config.configuracao
                
        elif config.condicao == 'hide':
            transaction['configuracao'] = 'hide'
        
        else:
            return transaction
    
    # se não encontrar a transação, procura pela transacao.value = '***' (não conhecida)
    transacao_db = tbTransacao.objects.filter(value='***').only('id').first()
    transaction['id'] = transacao_db.id if transacao_db else None

    return transaction
            
def convert_date(date_str) -> str:
    date = ""
    if date_str:
        try:
            date = datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            pass
    return date


def extract_cnpj(text):
    """
    Identifica e extrai CNPJs no formato XX.XXX.XXX YYYY-ZZ de um texto.
    """
    # Expressão regular para CNPJ
    cnpj_pattern = r'\b\d{2}\.\d{3}\.\d{3} \d{4}-\d{2}\b'

    # Procurar CNPJs no texto
    cnpjs = re.findall(cnpj_pattern, text)

    return cnpjs

def process_sicoob_input_xls(dataframe):
    # Preenche valores NaN com string vazia
    dataframe = dataframe.fillna('')

    # Criar colunas adicionais para as linhas complementares
    new_header = ['tipo', 'nome', 'nota', 'cpf', 'saldo']
    count_new_header = len(new_header) - 3  # não inclui 'nota' e 'saldo' na contagem
    for header in new_header:
        dataframe[header] = ''

    # Adicionar a nova coluna 'transaction'
    dataframe['debito'] = ''

    # Variáveis para armazenar o registro principal
    current_data = ''
    current_documento = ''
    current_historico = ''
    current_valor = ''

    # Lista para armazenar os registros reorganizados
    processed_data = []

    extra_line = 0
    # Iterar sobre as linhas do DataFrame
    for index, row in dataframe.iterrows():
        if row['data']:  # Linha principal
            extra_line = 0
            current_data = row['data']
            current_documento = row['documento']
            current_historico = row['historico']

            # Processar a coluna 'valor' para separar o valor numérico e a transação
            valor_str = row['credito']
            
            valor_float = float(valor_str[:-1].replace('.', '').replace(',', '.'))  # Remove ',' e '.' e converte para float
            
            debito = valor_float if valor_str[-1] == "D"  else ''  # Último caractere é 'C' ou 'D'
            current_valor = valor_float if valor_str[-1] == "C" else ''  # Último caractere é 'C' ou 'D'
            processed_data.append({
                'data': current_data,
                'documento': current_documento,
                'historico': current_historico,
                'credito': current_valor,
                'debito': debito,
                'tipo': '',
                'nome': '',
                'nota': '',
                'cpf': '',
                'saldo': '',
            })
        else:  # Linha adicional
            
            # Adicionar as informações complementares às colunas extras
            if row['historico']:

                header_ = new_header[extra_line]

                if row['historico'] in ['Pagamento Pix', 'Recebimento Pix', 'Transferência Pix', 'Transferência Bancária']:
                    header_ = 'tipo'
                    if row['historico'] == 'Pagamento Pix':
                        extra_line += 1
                        pass

                elif 'REM' in row['historico']:
                    header_ = ''
                    extra_line -= 1

                elif '**.' in row['historico']:
                    header_ = 'cpf'
                    extra_line -= 1

                elif 'SALDO DO DIA' in row['historico']:
                    header_ = ''
                    extra_line -= 1
                else:
                    cnpjs = extract_cnpj(row['historico'])
                    if cnpjs:
                        header_ = 'cpf'
                        row['historico'] = cnpjs[0]
                        extra_line -= 1

                if header_:
                    processed_data[-1][header_] = f"{processed_data[-1][header_]} {row['historico']}"

            if row['credito']:
                valor_str = row['credito']
                valor_float = float(valor_str[:-1].replace('.', '').replace(',', '.'))  # Remove ',' e '.' e converte para float
                if valor_str[-1] == 'D':
                    valor_float = -valor_float
                    
                processed_data[-1]['saldo'] = valor_float

            if row['documento']:
                processed_data[-1]['nota'] = f"{processed_data[-1][header_]} {row['documento']}"
            
            extra_line = (extra_line + 1) if extra_line < count_new_header else extra_line

    # Converter os dados processados em um novo DataFrame
    processed_df = pd.DataFrame(processed_data)

    return processed_df

import re
import pandas as pd
from datetime import datetime

def processar_sicoob_input_txt(file_name):
    """
    Processa o texto do extrato bancário e retorna um DataFrame.

    Args:
        texto_extrato (str): Texto completo do extrato bancário.

    Returns:
        pd.DataFrame: DataFrame contendo os dados processados do extrato.
    """
    error = ''

    # Abre o arquivo de texto
    with open(file_name, 'r', encoding='utf-8') as file:
        linhas = file.readlines()

    # Verifica se o texto está vazio
    if not linhas:
        error = f'O arquivo de extrato "{file_name}" está vazio.'
        return pd.DataFrame(), error

    if not "SICOOB - Sistema de Cooperativas de Crédito do Brasil" in linhas[0]:
        error = f'O arquivo "{file}" não e um extrato SICOOB válido'
        return pd.DataFrame(), error

    # Regex para identificar as linhas do extrato
    regex_linha = re.compile(r"(?P<data>\d{2}/\d{2}/\d{4})\s+")

    # Lista para armazenar os dados do extrato
    dados_extrato = []

    # Iterar pelas linhas e aplicar o regex
    for i, linha in enumerate(linhas):
        if linha:
            match = regex_linha.match(linha)
            if match:
                tipo = ""
                nome = ""
                cpf = ""
                nota = ""
                documento = ""
                historico = ""
                credito = ""
                debito = ""
                tab_historico = 32 # coluna do histórico
                tab_valor = 76 # coluna do valor
                
                if 'SALDO DO DIA' in linha:
                    tab_historico = linha.find('SALDO DO DIA')

                if 'EXTRATO CONTA CORRENTE' in linha or 'SALDO DO DIA' in linha:
                    continue

                # Extrair os dados da linha
                data = datetime.strptime(match.group("data"), "%d/%m/%Y").date()
            
                documento = linha[10:tab_historico].strip()  # Extrai o documento (pode ser vazio)  
                historico = linha[tab_historico:tab_valor:].strip()
                valor = linha[tab_valor:].strip()
                # Determinar se é crédito ou débito
                if valor.endswith("C"):
                    credito = float(valor[:-1].replace(".", "").replace(",", "."))
                    debito = None
                elif valor.endswith("D"):
                    debito = float(valor[:-1].replace(".", "").replace(",", "."))
                    if debito < 0:
                        debito = -debito
                    credito = None
                else:
                    credito = debito = None

                # Extrair informações adicionais do histórico (linhas subsequentes)
                additional_info = True
                next_line = i + 1
                rem = False
                while additional_info:
                    if next_line < len(linhas):
                        # Verifica se a próxima linha é uma linha adicional
                        if linhas[next_line].replace('-', '').strip() == "":
                            additional_info = False
                            continue

                        match = regex_linha.match(linhas[next_line])
                        if not match:
                            # Assume que as próximas linhas contêm informações adicionais
                            if next_line - i == 1:
                                if 'REM' in linhas[next_line]:
                                    rem = True
                                    nota += linhas[next_line].strip() + " "
                                else:
                                    tipo = linhas[next_line].strip() 
                            elif next_line - i == 2:
                                if rem:
                                    tipo = linhas[next_line].strip() 
                                else:
                                    nome = linhas[next_line].strip() 
                            elif next_line - i == 3:
                                if rem:
                                    nome = linhas[next_line].strip() 
                                else:
                                    cpf = linhas[next_line].strip()
                            elif next_line - i == 4:
                                if rem:
                                    cpf = linhas[next_line].strip()
                                else:
                                    nota += linhas[next_line].strip() + " "
                            elif 4 < (next_line - i) < 7:
                                 nota += linhas[next_line].strip() + " "
                            else:
                                additional_info = False
                            
                            next_line += 1
                        else:
                            # Se a próxima linha não for uma linha adicional, sai do loop
                            additional_info = False
                    else:
                        # Se não houver mais linhas, sai do loop
                        additional_info = False

                # print(i, data, documento, historico, credito, debito, tipo, nome, cpf, nota)
                # Adicionar os dados à lista
                dados_extrato.append({
                    "data": data,
                    "documento": documento,
                    "historico": historico,
                    "tipo": tipo,
                    "nome": nome,
                    "cpf": cpf,
                    "nota": nota,
                    "credito": credito,
                    "debito": debito,
                })

    # Criar o DataFrame a partir dos dados
    df_extrato = pd.DataFrame(dados_extrato)

    return df_extrato, error