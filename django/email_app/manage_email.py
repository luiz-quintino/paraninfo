from email.utils import formataddr, parseaddr
from django.conf import settings
from django.core.mail import send_mail
from config.constants import MESSAGE_TYPE_INFO, \
                             MESSAGE_TYPE_ERROR, \
                             MESSAGE_TYPE_WARNING, \
                             MESSAGE_TYPE_SUCCESS, \
                             MESSAGE_TYPE_CONFIRM
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from pathlib import Path
from products.models import tbMediaFiles
from users.models import tbAssociados
from html import escape

#*******************************************************************************************
# EMAIL_FICHA_DE_INSCRICAO_ATUALIZACAO
#*******************************************************************************************
EMAIL_FICHA_DE_INSCRICAO_ATUALIZACAO = """
Ilustre {},

Sua Ficha de Inscrição foi atualizada com sucesso.
Após a análise da documentação, você receberá um email de confirmação ou alguém irá entrar em contato com você. 


Utilize o link abaixo caso necessite alterar alguma informação ou algum docucumento.
Link para edição: {}
O link ficará disponível até que sua solicitação seja processada.

Esse é um email automático. Não responda a esse email

Atenciosamente,
{}
"""

#*******************************************************************************************
# EMAIL_FICHA_DE_INSCRICAO_ENVIO
#*******************************************************************************************
EMAIL_FICHA_DE_INSCRICAO_ENVIO = """
Ilustre {},

Temos o prazer de informar que a sua Ficha de Inscrição para a {} foi enviada com sucesso.
Após a análise da documentação, você receberá um email de confirmação ou alguém irá entrar em contato com você. 


Utilize o link abaixo caso necessite alterar alguma informação ou algum docucumento. 
Link para edição: {}
O link ficará disponível até que sua solicitação seja processada. 

Esse é um email automático. Não responda a esse email.

Atenciosamente,
{}
"""

#*******************************************************************************************
# EMAIL_FICHA_DE_INSCRICAO_APROVADA
#*******************************************************************************************
EMAIL_FICHA_DE_INSCRICAO_APROVADA = """
Olá, {}!

Gostaríamos de dar-lhe as boas vindas à {}

Estamos preparando tudo pra você.
Aguarde algumas horas e acesso o site paraninfo.com.br. Clique em [Esqueci minha senha] e siga as instruções para gerar uma senha e acessar o sistema.
Acesse o sistema para ver como está o seu pagamento, as últimas notícias e tudo relacionado ao evento de formatua.
O seu código de pagamento é: {}. Use este código nos centavos de cada pagamento que fizer à Comissão.
  Exemplo: Se o valor da mensalidade for R$ 100,00, pague R$ 100,{}, os centavos identificam que é você que está fazendo o pagamento.

Atenciosamente,
{},
"""

def send_paraninfo_email(request, subject, message_text, recipient_list) -> dict:
    email_error = {}
    recipient_list = recipient_list if isinstance(recipient_list, list) else [recipient_list]
    presidente_id = request.session['user_data']['comissao_presidente_id']
    presidente = tbAssociados.objects.filter(id=presidente_id).first()
    if presidente and presidente.email and presidente.email not in recipient_list:
        recipient_list.append(presidente.email)
            
    from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
	
    try:
        send_mail(
            subject=subject,
            message=(message_text),
            from_email=formataddr(('Paraninfo', from_address)),
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception as e:
        email_error = {
            'type': MESSAGE_TYPE_ERROR,
            'text': f'Não foi possível enviar o email. Erro: {str(e)}',
            'title': 'Erro ao enviar email',
        }

    return email_error


def purchase_mail(purchase_schedule, product, quantity, request, associado) -> bool:
    email_error = {}
    recipient_list = [associado.email]
    user_name = associado.nome_responsavel.split()[0].title()
    presidente_id = request.session['user_data']['comissao_presidente_id']
    presidente = tbAssociados.objects.filter(id=presidente_id).first()
    if presidente and presidente.email and presidente.email not in recipient_list:
        recipient_list.append(presidente.email)
			
    payment_text = ''.join([' '.join(['   ',f'{str(compra['number']):2}:',str(compra['due_date'].strftime("%d/%m/%Y")), f'R${compra["value"]:>8.2f}', '\n']) for compra in purchase_schedule])
    email_error = False 
    subject = f'Recebemos seu pedido para {product.produto}'
    
    success_message = (
        f'Compra realizada\n\n'
        f'Situação: Pendente de aprovação.\n\n'
        f'Produto: {product.produto}\n'
        f'Quantidade: {quantity}\n'
        f'{product.descricao}\n\n'
        f'Valor total: R${product.valor_total}\n'
        f'Plano de pagamento:\n{payment_text}\n\n'
        f'Atenciosamente,\n{request.comissao_title}'
    )

    from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
    email = EmailMultiAlternatives(
        subject=subject,
        body=success_message,
        from_email=formataddr(('Paraninfo', from_address)),
        to=recipient_list,
    )

    try:
        media = tbMediaFiles.objects.filter(id=product.img_id).first()
        image_html = ''
        if media:
            media_folder = media.folder.removeprefix('/media/').strip('/')
            image_path = (Path(settings.MEDIA_ROOT) / media_folder / media.new_file_name).resolve()
            if image_path.is_file():
                image_html = '<p><img src="cid:product-image" alt="Imagem do produto" style="max-width:500px;height:auto;"></p>'
                image = MIMEImage(image_path.read_bytes())
                image.add_header('Content-ID', '<product-image>')
                image.add_header('Content-Disposition', 'inline', filename=media.new_file_name)
                email.attach(image)

        subject = f'Olá {user_name}.\n{subject}'
        html_message = (
            f'<h2>{escape(subject)}</h2>'
            f'{image_html}'
            f'<p><strong>Situação:</strong> Pendente de aprovação.</p>'
            f'<p><strong>Produto:</strong> {escape(product.produto)}<br>'
            f'<strong>Quantidade:</strong> {quantity}<br>{escape(product.quantidade)}</p>'
            f'<p><strong>Valor total:</strong> R$ {product.valor_total}</p>'
            f'<p><strong>Plano de pagamento:</strong><br>{escape(payment_text).replace(chr(10), "<br>")}</p>'
            f'<p>Atenciosamente,<br>{escape(request.comissao_title or "Paraninfo")}</p>'
        )
        email.attach_alternative(html_message, 'text/html')
        email.send(fail_silently=False)

    except Exception as e:
        email_error = {
            'type': MESSAGE_TYPE_ERROR,
            'text': f'Não foi possível enviar o email. Erro: {str(e)}',
            'title': 'Erro ao enviar email',
        }

    return email_error


def purchase_approved_mail(product, request, associado, result) -> bool:
    recipient_list = [associado.email]
    user_name = associado.nome_responsavel.split()[0].title()
    presidente_id = request.session['user_data']['comissao_presidente_id']
    presidente = tbAssociados.objects.filter(id=presidente_id).first()
    if presidente and presidente.email and presidente.email not in recipient_list:
        recipient_list.append(presidente.email)
		
    email_error = False
    subject = f'Esse é o resultado do seu pedido para {product.produto}'
    success_message = (
		f'Situação da Compra: {result}.\n\n'
		f'Produto: {product.produto}\n'
		f'{product.descricao}\n\n'
		f'Valor total: R${product.valor_total}\n'
		f'Atenciosamente,\n{request.comissao_title}'
	)
	
    from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
    email = EmailMultiAlternatives(
        subject=subject,
        body=success_message,
        from_email=formataddr(('Paraninfo', from_address)),
        to=recipient_list,
    )
    try:
        media = tbMediaFiles.objects.filter(id=product.img_id).first()
        image_html = ''
        if media:
            media_folder = media.folder.removeprefix('/media/').strip('/')
            image_path = (Path(settings.MEDIA_ROOT) / media_folder / media.new_file_name).resolve()
            if image_path.is_file():
                image_html = '<p><img src="cid:product-image" alt="Imagem do produto" style="max-width:500px;height:auto;"></p>'
                image = MIMEImage(image_path.read_bytes())
                image.add_header('Content-ID', '<product-image>')
                image.add_header('Content-Disposition', 'inline', filename=media.new_file_name)
                email.attach(image)
        subject = f'Olá {user_name}.\n{subject}'
        html_message = (
			f'<h2>{escape(subject)}</h2>'
			f'{image_html}'
			f'<p><strong>Situação da compra:</strong> {escape(result)}</p>'
			f'<p><strong>Produto:</strong> {escape(product.produto)}<br>'
			f'<strong>Quantidade:</strong> {escape(product.quantidade)}</p>'
			f'<p><strong>Valor total:</strong> R$ {product.valor_total}</p>'
			f'<p>Atenciosamente,<br>{escape(request.comissao_title or "Paraninfo")}</p>'
		)
        email.attach_alternative(html_message, 'text/html')
        email.send(fail_silently=False)
		
    except Exception as e:
        email_error = {
            'type': MESSAGE_TYPE_ERROR,
            'text': f'Não foi possível enviar o email. Erro: {str(e)}',
            'title': 'Erro ao enviar email',
        }

    return email_error