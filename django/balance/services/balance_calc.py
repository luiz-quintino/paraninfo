from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from config.constants import MONTHS
from pathlib import Path
from transaction.models import tbExtrato, tbTransacao, lsttransacao, tbAssociados
from balance.models import tbRelatorio

from datetime import datetime, date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PyPDF2 import PdfFileReader, PdfFileWriter
from PIL import ImageFont
from products.models import tbCompra, tbParcelamento
from paraninfo_admin.models import tbComissao
import io
import os
import copy
import json
import math

def month_enclosed(comissao: dict, extratos):
    """
        Realiza o fechamento mensal do mês anterior
    """

    sequence = comissao['sequence']     # 8
    title = comissao['title']           # 'COMISSÃO DE FORMATURA DOS SÓCIOS TURMAS DO 6º ANO 2023'
    inscricao = comissao['inscricao']   # '1478340/001-2'
    cnpj = comissao['cnpj']             # '50.945.607/0001-12'
    comissao_id = comissao['comissao_id']
    year = comissao['year']
    month = comissao['month']

    main_data =  {'comissao_id': comissao_id, 'year':year, 'month':month, 'sequence':sequence}

    # Filtra as transações e lista em ordem inversa de data e id, para que as transações mais recentes venham primeiro
    transaction_report = tbTransacao.objects.filter(
        comissao_id=comissao_id,
    ).order_by('-data', '-id')

    # Reagata o valor das aplicações do mês anterior, se houver, para somar ao saldo final do mês
    t_aplicacao = float(transaction_report.filter(
        transacao__key_name='TotalAplicacao'
    )[0].valor) if transaction_report.filter(transacao__key_name='TotalAplicacao').exists() else 0.0    

    # Extrai key, value de tbTransacao
    transaction_list = lsttransacao.objects.filter()
    popup_list = []
    for transacao_ in transaction_list:
        popup_list.append(transacao_.key_name)

    # Cria o caminho do modelo de relatório em PDF e da pasta onde será salvo o relatório
    # TODO colocar em um db os recursos
    model_name = os.path.join(Path(settings.RESOURCES_ROOT), 'livro_caixa_template.pdf')  
    folder_name = f'media/{str(comissao_id)}/reports/{str(year)}'

    # Cria uma lista de dicionários com os dados dos extratos
    data_list = []
    for extrato in extratos:
        data_list.append({
            'data': {'value': extrato.data.strftime('%d/%m/%Y')},
            'operacao': {'value': extrato.historico},
            'credito': {'value': float(extrato.credito) if extrato.credito else 0.0},
            'debito': {'value': float(extrato.debito) if extrato.debito else 0.0},
            'nota': {'value': extrato.transacao.key_name if extrato.transacao else ''},
            'user*': {'value': str(extrato.associado_id)},
            'doc': {'value': ''},
            'cc': {'value': 'CC'}
        })

    # Cria configurações para o relatório
    config = {
        'title': title,
        'inscription': inscricao,
        'cnpj': cnpj,
        'month': MONTHS.get(month,1),
        'doc': str(sequence).zfill(2),
        'hash': f'{comissao_id}-{year}-{month}',
        'popup': popup_list,
        "t_aplicacao": t_aplicacao,
        'signatures': [
            {'title': 'Comissão de Formatura', 'name': 'Presidente', 'document': ''},
            {'title': 'Comissão de Formatura', 'name': 'Tesoureiro', 'document': ''},
            {'title': 'Comissão de Formatura', 'name': 'Secretário', 'document': ''}
        ],
        'folder_name': settings.BASE_DIR / folder_name,
        'model_name': model_name
    }

    
    # *******************************************************************************************************************************
    # Cria o relatório em PDF usando o modelo e os dados coletados
    # *******************************************************************************************************************************
    error = {}
    try:
        file_name, totals = create_account_report(data_list, config)
    except Exception as e:
        error['report'] = e

    # *******************************************************************************************************************************
    #  Atualiza tbTransacao com os valores totais de cada tipo de transação 
    # *******************************************************************************************************************************
    if not error:
        try:
            update_transactions(transaction_list, transaction_report, totals, main_data)
        except Exception as e:
            error['update_transaction'] = e

    if not error:
        # Atualiza extrato status = 3
        extratos=tbExtrato.objects.filter(
        comissao_id=comissao_id,
        data__year=year,
        data__month=month,
        status=2, # Extratos prontos para fechamento
        id=1600,
        ).update(status=3)


        # *******************************************************************************************************************************
        #  Atualiza a situação dos pagamentos dos associados
        # *******************************************************************************************************************************
        update_associado(comissao_id)


        # *******************************************************************************************************************************
        #  Atualiza fechamento em tbComissao
        # *******************************************************************************************************************************
        mes = month + 1 if month < 12 else 1
        ano = year +1 if month == 12 else year
        sequence += 1
        tbComissao.objects.filter(id=comissao_id).update(ano=ano, mes=mes, sequence=sequence)

        tbRelatorio.objects.create(
            comissao_id=comissao_id,
            sequencia=sequence,
            arquivo=file_name,
            pasta=folder_name,
            data=date.today()
        )


def update_associado(comissao_id):
    associados = tbAssociados.objects.filter(
        comissao=comissao_id,
        situacao='Ativo'  # Associado ativo
    )

    today = date.today()
    for associado in associados:
        summary = user_balance(associado, today)
        if summary['fine'] > 0 :
            print(associado.nome_responsavel, summary['balance'], summary['fine'], summary['interest'], summary['plan'])
            parcelamento = tbParcelamento.objects.create(
                            plano_pagamento = summary['plan'],
                            parcela_numero = 0,
                            valor = summary['fine'],
                            dt_vencimento = today,
                            origem = 3  # parcela atuomática
                        ).save()
            
        if summary['interest'] > 0:
            parcelamento = tbParcelamento.objects.create(
                            plano_pagamento = summary['plan'],
                            parcela_numero = 0,
                            valor = summary['interest'],
                            dt_vencimento = today,
                            origem = 4  # parcela atuomática
                        ).save()



def update_transactions(transaction_list, transaction_report, totals, main_data):
    avoid_duplicates = ['Saldo Inicial']
    for transaction_ in transaction_list:
        # pega o último valor de transaction_.key_name em tbTransacao
        if transaction_.key_name in avoid_duplicates:
            continue

        avoid_duplicates.append(transaction_.key_name)
        valor = 0.0
        
        # Pego o valor anterior da transação para somar ao atual
        last_transaction = transaction_report.filter(transacao__key_name=transaction_.key_name).first()
        if last_transaction and transaction_.key_name not in ['Total Credito', 'Total Debito', 'Saldo CC', 'Saldo CC Total CC + Apl']:
            valor = float(last_transaction.valor)
    
        # soma com o valor atual de transaction_.key_name de totals, se existir
        if transaction_.key_name in totals:
            valor = valor + float(totals[transaction_.key_name])

        # cria um novo registro em tbTransacao com o valor total de cada tipo de transação no mês
        tbTransacao.objects.create( 
            sequencia=main_data.get('sequence'),
            data=date(main_data.get('year'), main_data.get('month'), 1),
            comissao_id=main_data.get('comissao_id'),
            transacao=transaction_,
            valor=valor
        ).save()


def create_account_report(data_list: list, config: dict) -> dict:
    """ Cria o relatório em PDF usando o modelo e os dados coletados """
    pdf_in = PdfFileReader(config.get('model_name'))
    pdf_out = PdfFileWriter()

    current_year = str(datetime.strptime(data_list[0]['data'].get('value'), '%d/%m/%Y').year)
    current_date = date.today().strftime("%d/%m/%Y")
    current_month = config.get('month')
    doc_number = config.get('doc','')
    sig_hash = config.get('hash','')
    cnpj = config.get('cnpj','')
    inscription = config.get('inscription','')
    title = config.get('title','')[:60]

    items = len(data_list)
    l_pages = ([35] * ((items + 10) // 35)) if items > 34 else [items] if items > 24 else []
    l_pages += [(items + 10) % 35] if items > 35 else [items] if items < 25 else [35 - items]
    # l_pages = [5, 16, 8, 5]
    font_file = os.path.join(Path(settings.RESOURCES_ROOT), 'resources/times.ttf')
    # pdfmetrics.registerFont(TTFont('Times-Roman', font_file._str)) #??
    font = ImageFont.truetype(font_file, 12)
    # sizex, sizey = font.getsize('A')
    sizex = math.ceil(pdfmetrics.stringWidth('A', 'Times-Roman', 12)) 
    ascent,descent = pdfmetrics.getAscentDescent('Times-Roman', 12)
    sizey = math.ceil(ascent - descent) 
    t_cred = 0
    t_deb = 0
    totals = {}
    for page in range(len(l_pages)):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
        can.setFont('Times-Roman', 12)

        start_line = 820
        pag_number = f'{page + 1}/{len(l_pages)}'
        can.drawString((7 + (64-len(title))/2) * sizex, start_line - sizey * 3, title)
        can.drawString(7 * sizex, start_line - sizey * 11, current_year)
        can.drawString(14 * sizex, start_line - sizey * 11, current_date)
        can.drawString(23 * sizex, start_line - sizey * 11, inscription)
        can.drawString(34 * sizex, start_line - sizey * 11, cnpj)

        can.drawString(50 * sizex, start_line - sizey * 11, doc_number)
        can.drawString(57 * sizex, start_line - sizey * 11, pag_number)
        can.drawString(6 * sizex, start_line - sizey * 13, f'Ref. {current_month}')
        can.setFont('Times-Roman', 10)
        can.drawString(39 * sizex, start_line - sizey * 13, sig_hash)

        col = [7, 13, 35, 40, 46, 61]
        start_line = 57 * sizey
        # can.setFont('Times-Roman', 10)
        for row, data_row in enumerate(data_list):
            if sum(l_pages[:page]) <= row < sum(l_pages[:page + 1]):
                key = data_row['nota']['value'].split(':')[0]
                if key in config.get('popup'):
                    totals[key] = (data_row['credito']['value'] + data_row['debito']['value'] +
                                                    totals.get(key, 0.0))

                for column, (key, item) in enumerate(data_row.items()):
                    if column < len(col):
                        if key == 'credito':
                            t_cred += item.get('value')
                            if item.get("value"):
                                can.drawString(col[column] * sizex, start_line - (row - sum(l_pages[:page])) * 15,
                                                f'{item.get("value"):0.2f}')
                        elif key == 'debito':
                            t_deb += item.get('value')
                            if item.get("value"):
                                can.drawString(col[column] * sizex, start_line - (row - sum(l_pages[:page])) * 15,
                                                f'{item.get("value"):0.2f}')
                        elif key == 'nota':
                            note = item.get('value') + ' ' + data_row['user*'].get('value') + ' ' + data_row[
                                'doc'].get('value')
                            can.drawString(col[column] * sizex, start_line - (row - sum(l_pages[:page])) * 15,
                                            note)
                        elif key == 'user*':
                            note = 'cc' if data_row['cc'].get('value') else '$'
                            can.drawString(col[column] * sizex, start_line - (row - sum(l_pages[:page])) * 15,
                                            note)
                        else:
                            can.drawString(col[column] * sizex, start_line - (row - sum(l_pages[:page])) * 15,
                                            str(item.get('value')))
                can.drawString(5 * sizex, start_line - (row - sum(l_pages[:page])) * 15, f'{row}')

        # Posição das assinaturas
        coli = [105, 270, 435]
        rowi = [50, 125]
        can.setFont('Times-Roman', 10)

        if page == len(l_pages) - 1:
            # Insere a soma total na última página
            row = l_pages[-1]   # última linha de dados

            can.drawString(5 * sizex, start_line - (row + 0) * 15, 156 * '-')
            can.drawString(col[2] * sizex, start_line - (row + 1) * 15, f'{t_cred:0.2f}')
            can.drawString(col[3] * sizex, start_line - (row + 1) * 15, f'{t_deb:0.2f}')
            can.drawString(5 * sizex, start_line - (row + 2) * 15, 156 * '-')

            can.drawString(col[1] * sizex, start_line - (row + 3) * 15, 'SALDO CC ==>')
            can.drawString(col[2] * sizex, start_line - (row + 3) * 15, f'{t_cred - t_deb:0.2f}')

            if config.get("t_aplicacao") > 0:
                can.drawString(col[1] * sizex, start_line - (row + 4) * 15, 'SALDO INVESTIMENTOS ==>')
                can.drawString(col[2] * sizex, start_line - (row + 4) * 15, f'{config.get("t_aplicacao"):0.2f}')
                can.drawString(col[1] * sizex, start_line - (row + 5) * 15, 'SALDO TOTAL ==>')
                can.drawString(col[2] * sizex, start_line - (row + 5) * 15, f'{config.get("t_aplicacao") + t_cred - t_deb:0.2f}')

            names = config.get('signatures')
            for i in range(6):
                if len(names) > i:
                    can.drawString(coli[i % 3] - sizex / 2, rowi[i // 3], names[i].get('name'))
                    can.drawString(coli[i % 3] - sizex / 2, rowi[i // 3] + 15, names[i].get('title'))
                    can.drawString(coli[i % 3] - sizex / 2, rowi[i // 3] + 15 * 2, names[i].get('document'))

        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        pdf_ref = copy.deepcopy(pdf_in)

        pdf_ref.pages[0].mergePage(new_pdf.pages[0])
        pdf_out.addPage(pdf_ref.pages[0])

    file_name = f'{current_year}-{current_month}-livro caixa.pdf'

    totals['Total Credito'] = t_cred
    totals['Total Debito'] = t_deb
    totals['Saldo CC'] = f'{t_cred - t_deb:0.2f}'
    totals['Saldo CC Total CC + Apl'] = f'{config.get("t_aplicacao") + t_cred - t_deb:0.2f}'

    # Cria o caminho, se não existe
    os.makedirs(config.get('folder_name'), exist_ok=True)

    with open(os.path.join(config.get('folder_name'), file_name), 'wb') as of:
        pdf_out.write(of)

    return file_name, totals


def user_balance(associado, today):
    rows = []
    extratos = tbExtrato.objects.filter(associado_id=associado.id).select_related('transacao').order_by('data', 'id')
    for extrato in extratos:
        paid = extrato.credito or Decimal('0.00')
        received = Decimal('0.00')
        if paid == 0 and (extrato.debito or Decimal('0.00')) > 0:
            received = extrato.debito
        rows.append({
            'date': extrato.data,
            'paid': paid,
            'debit': Decimal('0.00'),
            'received': received,
            'description': extrato.transacao.key_name if extrato.transacao else '',
            'product_uuid': None,
            'order': extrato.id,
        })

    purchases = list(
        tbCompra.objects.filter(
            associado_id=associado.id,
            status=tbCompra.STATUS_APROVADO,
        ).select_related('produto').order_by('id')
    )
    plan_codes = {purchase.plano_pagamento for purchase in purchases if purchase.plano_pagamento}
    schedules = tbParcelamento.objects.filter(
        plano_pagamento__in=plan_codes
    ).order_by('dt_vencimento', 'id')
    products_by_plan = {
        purchase.plano_pagamento: purchase.produto
        for purchase in purchases
        if purchase.plano_pagamento and purchase.produto
    }
    for installment in schedules:
        product = products_by_plan.get(installment.plano_pagamento)
        if not product:
            continue

        product_description = 'multa' if installment.origem == 4 else 'juros' if installment.origem == 3 else product.produto
        # TODO Não mostra link para produto sem uuid
        product_uuid = associado.uuid if installment.origem < 3 else None
        rows.append({
            'date': installment.dt_vencimento,
            'paid': Decimal('0.00'),
            'debit': installment.valor,
            'received': Decimal('0.00'),
            'description': product_description,
            'product_uuid': product_uuid,
            'order': 1_000_000_000 + installment.id,
            'plan': list(plan_codes)
        })

    summary = _payment_history_summary(rows, today, associado)
    return summary

def _payment_history_summary(rows, today, associado):
    rows = sorted(rows, key=lambda row: (row['date'], row.get('order', 0)))
    past_rows = [row for row in rows if row['date'] <= today]
    future_rows = [row for row in rows if row['date'] > today]

    total_paid = sum((row['paid'] for row in past_rows), Decimal('0.00'))
    total_debit = sum((row['debit'] for row in past_rows), Decimal('0.00'))
    total_received = sum((row['received'] for row in past_rows), Decimal('0.00'))
    grand_total_paid = sum((row['paid'] for row in rows), Decimal('0.00'))
    grand_total_debit = sum((row['debit'] for row in rows), Decimal('0.00'))
    grand_total_received = sum((row['received'] for row in rows), Decimal('0.00'))
    balance = total_paid - total_debit
    plan_ = [row['plan'] for row in rows if (row['date'] <= today and row.get('plan'))]
    plan = None if not plan_ else plan_[-1][-1]

    last_debit_date = max(
        (row['date'] for row in past_rows if row['debit'] > 0),
        default=None,
    )

    if balance < 0:
        if last_debit_date is None:
            last_debit_date = min(
                (row['date'] for row in past_rows if row['paid'] > 0),
                default=today,)
            
        overdue_days = max(0, (today - last_debit_date).days)
        fine = (-balance * Decimal('0.02')).quantize(Decimal('0.01'))
        interest = (
            -balance * Decimal('0.00033') * overdue_days
        ).quantize(Decimal('0.01'))

    else:
        overdue_days = 0
        fine = Decimal('0.00')
        interest = Decimal('0.00')

    next_debit = sum(
        (
            row['debit']
            for row in future_rows
            if row['debit'] > 0
            and row['date'].year == today.year
            and row['date'].month == today.month
        ),
        Decimal('0.00'),
    )
    # show_next_payment = next_debit > 0 or balance < 0
    show_next_payment = True

    # Converte o código de pagamento em valor decimal para os centavos
    codigo_pagamento_ = (associado.codigo_pagamento if associado.codigo_pagamento else 0)/100
    codigo_pagamento_ = 0 if codigo_pagamento_ >= 1 else codigo_pagamento_
    codigo_pagamento = Decimal(f'{codigo_pagamento_:.2f}').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    next_payment = ((next_debit + max(Decimal('0.00'), -balance) + fine + interest)
        .quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    
    next_payment = next_payment + codigo_pagamento if show_next_payment else None
    

    return {
        'past_rows': past_rows,
        'future_rows': future_rows,
        'total_paid': total_paid,
        'total_debit': total_debit,
        'total_received': total_received,
        'grand_total_paid': grand_total_paid,
        'grand_total_debit': grand_total_debit,
        'grand_total_received': grand_total_received,
        'balance': balance,
        'fine': fine,
        'interest': interest,
        'overdue_days': overdue_days,
        'next_debit': next_debit,
        'next_payment': next_payment,
        'next_payment_month': MONTHS[today.month].title(),
        'show_next_payment': show_next_payment,
        'plan': plan
    }