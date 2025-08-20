from transaction.models import tbExtrato

def month_enclosed(comissao_id, year, month):
    """
        Realiza o fechamento mensal do mês anterior
    """

    # Filtra os extratos do mês anterior
    extratos = tbExtrato.objects.filter(
        comissao_id=comissao_id,
        data__year=year,
        data__month=month,
        status=2 # Extratos prontos para fechamento
    )

    user = {'associado_id': 0, 'pagamentos': {'total_pago': 0, 'total_creditos': 0, 'total_outros': 0, 'total_em_aberto': 0, 'total_credito_acordo': 0, 'valor_mens_acordo': 0, 'valor_entrada_acordo': 0}}
    config = {'comissao_id': 1, 'valor_mensalidade': 140, 'valor_anterior': 140, 'objetivo_mensalidade': 1000, 'n_associados': 37, 'mes_fechamento': 7}
    totals = {'name': 'total', 'value': 0}
    boletos = {'associado_id': 0, 'boletos': [{'vencimento': '2023-10-01', 'valor': 140, 'quitata': False}]}

    for extrato in extratos:
        user_id = extrato.associado.id if extrato.associado else None
        transacao_key = extrato.transacao.key if extrato.transacao else None
        transacao_totals = extrato.transacao.value if extrato.transacao else None
        
        if user_id:
            if user_id not in user:
                user[user_id] = {
                    'total_pago': 0,
                    'total_creditos': 0,
                    'total_outros': 0,
                    'total_em_aberto': 0,
                    'total_acordo': 0
                }

            if transacao_key == 'Mensalidade associado':  # Pagamento de mensalidade
                # valor pago deve ser mair que mensalidade
                mens_pagas = extrato.credito
                if mens_pagas >= config['valor_mensalidade']:
                    # caso seja, deve gerar crédito 
                    total_credito = mens_pagas - config['valor_mensalidade']
                    mens_pagas = config['valor_mensalidade']

                else:
                    # caso não seja, deve verificar se possui crédito e usá-lo
                    mens_pagas += user[user_id]['total_creditos']
                    if mens_pagas >= config['valor_mensalidade']:
                        total_credito = mens_pagas - config['valor_mensalidade']
                        mens_pagas = config['valor_mensalidade']
                        # desconta o valor utilizado no crédito
                        total_credito = - (user[user_id]['total_creditos'] - total_credito)
                        
                    else:
                        # caso não tenha crédito, verifica se tem acordo
                        acordo_ = user[user_id]['pagamentos']['total_credito_acordo']
                        if acordo_ > mens_pagas:
                            mens_pagas = extrato.credito
                            user[user_id]['pagamentos']['total_credito_acordo'] -= user[user_id]['pagamentos']['valor_mens_acordo']
                            user[user_id]['pagamentos']['total_credito_acordo'] = 0 if user[user_id]['pagamentos']['total_credito_acordo'] < 0 else user[user_id]['pagamentos']['total_credito_acordo']
                        
                        else:

                            total_debito = config['valor_mensalidade'] - mens_pagas
                            mens_pagas = extrato.credito

            elif transacao_key == 'Mensalidade em atraso ass':
                mens_pagas = extrato.credito
                for boleto in boletos[user_id]['boletos']:
                    if mens_pagas > boleto['valor'] and not boleto['quitata']:
                        boleto['quitada'] = True
                        total_outros = mens_pagas - boleto['valor']
                        mens_pagas -= total_outros
                
            elif transacao_key == 'Primeira mensalidade ass':
                # valor pago deve ser maior que o objetivo das mensalidades
                dif = extrato.credito - config['objetivo_mensalidade']

                if dif < 0:
                    # caso não seja e tenha acordo, acordo deve cobrir o valor pago
                    acordo_ = user['associado_id']['valor_entrada_acordo'] + dif
                    user['associado_id']['valor_entrada_acordo'] = 0
                    mens_pagas = extrato.credito
                    if acordo_ < 0:
                        # caso não cubra, será gerado débito
                        total_debito = - acordo_

                else:
                    # valor pago cobriu mensalidades e pode ter gerado crédito
                    total_credito = dif
                    mens_pagas = extrato.credito - dif

            user[user_id] = {
                    'total_pago': mens_pagas,
                    'total_creditos': total_credito,
                    'total_outros': total_outros,
                    'total_em_aberto': total_debito,
                    'total_acordo': total_acordo
                }
                  


