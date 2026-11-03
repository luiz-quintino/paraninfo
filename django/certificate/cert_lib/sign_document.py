from .__init__ import *
from . import cert_parser as cp
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.sign import fields, signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils import text, images
from pyhanko import stamp
from pyhanko.sign.signers.pdf_byterange import BuildProps
from PIL import ImageFont
from reportlab.pdfbase import pdfmetrics
from django.conf import settings
from ..models import tbCertificados
from users.models import tbAssociados
from .create_certificate import create_root_certificate, \
                                create_intermediate_certificate, \
                                create_user_certificate
import math
import os
from io import BytesIO

def signing_by_cert_id(file_pdf, cert_id, index_position, user_id, comissao):
    # TODO quando não tem cert, tem que trazê-lo ao criá-lo
    cert = tbCertificados.objects.filter(id=cert_id).first()
    if not cert:
        cert_id = install_user_certificate_and_check_validity(cert_id, user_id, comissao)
        cert = tbCertificados.objects.filter(id=cert_id).first()
        # TODO cert_id = 0 / cert = ''

    cert_root = tbCertificados.objects.filter(
            situacao=tbCertificados.STATUS_VALIDO,
            tipo=tbCertificados.TYPE_ROOT_CA
        ).first()
    
    cert_intermediate = tbCertificados.objects.filter(
                situacao=tbCertificados.STATUS_VALIDO,
                tipo=tbCertificados.TYPE_INTERMEDIATE_CA
            ).first()
    
    file_root = f'{cert_root.arquivo}.pem'
    file_intermediate = f'{cert_intermediate.arquivo}.pem'

    file_cert = f'{cert.arquivo}.pem'
    file_key = f'{cert.arquivo}.key'
    password = cert.senha
    signed_file_name = sign_pdf(file_name=file_pdf, key_file=file_key,password= password, cert_file= file_cert, cert_chain=[file_root, file_intermediate], index_position=index_position)

    return signed_file_name, cert_id 

def assinar_pdf(input_stream, output_stream, sig_name, box_coords, key_file, password, cert_file, cert_chain, txt, sign_image):
    # 1. Inicializa o escritor incremental com o stream atual (arquivo original ou previamente assinado)
    w = IncrementalPdfFileWriter(input_stream)

    # 2. Adiciona o campo de assinatura correspondente no PDF
    fields.append_signature_field(
        w, 
        SigFieldSpec(
            sig_field_name=sig_name, 
            box=box_coords,
            field_mdp_spec=fields.FieldMDPSpec(fields.FieldMDPAction.ALL),
            on_page=-1,
            # ATENÇÃO: FILL_FORMS permite que novas assinaturas sejam adicionadas depois sem invalidar esta
            doc_mdp_update_value=fields.MDPPerm.FILL_FORMS, 
        )
    )

    # 3. Metadados da assinatura atual
    meta_data = signers.PdfSignatureMetadata(
        field_name=sig_name,
        reason='Confirmo a veracidade e integridade deste documento',
        location='Belo Horizonte/MG',
        app_build_props=BuildProps('Comissao de Formatura')
    )

    # 4. Configuração do Signatário (Chave e Certificado)
    signer = signers.SimpleSigner.load(
        key_file=key_file,
        key_passphrase=str(password).encode(),
        cert_file=cert_file,
        ca_chain_files=cert_chain
    )

    # 5. Estilo do Carimbo/Visual da Assinatura
    stampstyle = stamp.TextStampStyle(
        stamp_text=txt,
        text_box_style=text.TextBoxStyle(),
        timestamp_format='%d/%m/%Y %H:%M:%S %Z',
        background=images.PdfImage(str(sign_image)),
        border_width=0
    )

    out = signers.PdfSigner(
        signature_meta=meta_data,
        signer=signer,
        stamp_style=stampstyle
    )

    # 6. Aplica a assinatura gerando um buffer de saída intermediário
    out_buf = BytesIO()
    out.sign_pdf(w, output=out_buf)
    out_buf.seek(0)
    
    # Escreve o resultado final no stream de saída fornecido
    output_stream.write(out_buf.read())


def sign_pdf(file_name: str, key_file: str, password: bytes, cert_file: str, cert_chain: list, index_position):
    # Assina um documento PDF na posição definida em index_position: matrix 3x4 da esquerda pra direita de baixo pra cima
    cert = cp.CertificateParser(fio.open_file(cert_file))
    dn = ''.join([val._attributes[0].rfc4514_attribute_name + '= ' + val._attributes[0].value + ', '
                    for val in cert.subject._attributes]).strip(', ')
    dn = '\n'.join(get_text_line('DN: {}'.format(dn), limit=280))
    txt = 'Assinado digitalmente por: %(signer)s\n' + dn + 'Data: %(ts)s'
    x = [70, 240, 410]
    y = [130, 190, 260, 330]
    # só pra teste, é possível assinar 12 vezes com a mesma assinatura
    sig_list = range(12)
    index_position = 11 if index_position > 11 else index_position
    sig_list=[index_position]

    box = []
    for y_ in y:
        for x_ in x:
            box.append([x_, y_, x_+140, y_-45])

    # Carrega a imagem de fundo uma única vez
    sign_image_file = 'chapeu.jpg'
    sign_image = [dir_ / sign_image_file for dir_ in settings.STATICFILES_DIRS if os.path.exists(dir_ / sign_image_file)][0]

    file_base = os.path.splitext(file_name)[0]
    already_signed =  file_base.find('.signed_')
    if already_signed > 0:
        file_base = file_base[:already_signed]
    file_name_ = file_name

    for sig_ in sig_list:
        intermediate_file = f"{file_base}.signed_{sig_}.pdf"
        with open(file_name, 'rb') as inf, open(intermediate_file, 'wb') as outf:
            assinar_pdf(
                input_stream=inf,
                output_stream=outf,
                sig_name=f'Assinatura{sig_}',
                box_coords=box[sig_],
                key_file=key_file, password=password, cert_file=cert_file, cert_chain=cert_chain,
                txt=txt, sign_image=sign_image
            )
        os.remove(file_name)
        file_name = intermediate_file

    os.rename(intermediate_file, file_name_)
    return file_name_


def sign_pdf2(file_name: str, key_file: str, password: bytes, cert_file: str, cert_chain: list, x=220, y=130):
    cert = cp.CertificateParser(fio.open_file(cert_file))
    dn = ''.join([val._attributes[0].rfc4514_attribute_name + '= ' + val._attributes[0].value + ', '
                    for val in cert.subject._attributes]).strip(', ')
    dn = '\n'.join(get_text_line('DN: {}'.format(dn), limit=280))
    txt = 'Assinado digitalmente por: %(signer)s\n' + dn + 'Data: %(ts)s'

    with open(file_name, 'rb+') as doc:
        w = IncrementalPdfFileWriter(doc)
        x = [70, 220, 400]
        y = 130

        append_signature_field(w, SigFieldSpec(sig_field_name="Assinatura", box=(x, y, x + 140, y - 45),
                                                field_mdp_spec=fields.FieldMDPSpec(fields.FieldMDPAction.ALL),
                                                on_page=-1,
                                                doc_mdp_update_value=fields.MDPPerm.NO_CHANGES, ), )

        meta_data = signers.PdfSignatureMetadata(field_name='Assinatura',
                                                    reason='Confirmo a veracidade e integridade deste documento',
                                                    location='Belo Horizonte/MG',
                                                    app_build_props=BuildProps('Comissao de Formatura'))

        signer = signers.SimpleSigner.load(key_file=key_file,
                                            key_passphrase=str(password).encode(),
                                            cert_file=cert_file,
                                            ca_chain_files=cert_chain)

        sign_image_file = 'chapeu.jpg'
        sign_image = [dir_ / sign_image_file for dir_ in settings.STATICFILES_DIRS if os.path.exists(dir_ / sign_image_file)][0]
        
        stampstyle = stamp.TextStampStyle(stamp_text=txt,
                                            text_box_style=text.TextBoxStyle(),  # (font=font),
                                            timestamp_format='%d/%m/%Y %H:%M:%S %Z\'',
                                            background=images.PdfImage(str(sign_image)),
                                            border_width=0)

        out = signers.PdfSigner(signature_meta=meta_data,
                                signer=signer,
                                stamp_style=stampstyle)

        file_name = os.path.splitext(file_name)[0]
        with open(file_name + '.signed.pdf', 'wb') as outf:
            out.sign_pdf(w, output=outf)

    os.remove(file_name + '.pdf')
    return file_name + '.signed.pdf'

def get_text_line(text, start=0, end=None, limit=470) -> list:
    out_text = []
    text += ' '
    if end is None:
        end = len(text)
    font = ImageFont.truetype('resources/times.ttf', 11)
    for i in range(len(text)):
        spc = text.rfind(' ', start, end)
        spc1 = text.rfind(',', start, end)
        spc = spc if spc1 < spc else spc1
        if spc > 0:
            # sizex, sizey = font.getsize(text[: spc])
            sizex = math.ceil(pdfmetrics.stringWidth(text[: spc], 'Times-Roman', 11)) 
            # ascent,descent = pdfmetrics.getAscentDescent('Times-Roman', 11)
            # sizey = math.ceil(ascent - descent)
            if sizex < limit:
                out_text.append(text[start: spc].strip())
                text = text[spc:]
                end = len(text)
            else:
                end = spc
        else:
            # sizex, sizey = font.getsize(text)
            sizex = math.ceil(pdfmetrics.stringWidth(text, 'Times-Roman', 11)) 
            # ascent,descent = pdfmetrics.getAscentDescent('Times-Roman', 11)
            # sizey = math.ceil(ascent - descent)
            if sizex < limit:
                out_text.append(text.strip())
                break
            else:
                for j in range(len(text)):
                    # sizex, sizey = font.getsize(text[start:j])
                    sizex = math.ceil(pdfmetrics.stringWidth(text[start:j], 'Times-Roman', 11))
                    if sizex > limit:
                        out_text.append(text[start:j - 1].strip())
                        start = j - 1
    return out_text

def install_user_certificate_and_check_validity(cert_id, user_id, comissao):
    """
        This function install user certificates.
    """
    validate_user = datetime.today().date()

    if cert_id:
        certificado = tbCertificados.objects.filter(
                id=cert_id,
            ).first()
        if certificado:
            validate_user = certificado.validade
    
    if validate_user <= datetime.today().date():
        # atualizado o user existente para vencido, se existir
        if cert_id:
            tbCertificados.objects.filter(
                    id=cert_id,
                ).update(situacao=tbCertificados.STATUS_VENCIDO)
        
        intermediate = tbCertificados.objects.filter(
                situacao=tbCertificados.STATUS_VALIDO,
                tipo = tbCertificados.TYPE_INTERMEDIATE_CA,
            ).first()

        password = intermediate.senha
        file_name = intermediate.arquivo
        associado = tbAssociados.objects.filter(id=user_id).first()
        data_dict = {
                        'Nascimento': associado.nascimento_responsavel.strftime('%Y-%m-%d'),
                        'Código associado': associado.codigo_associado,
                        'Nome de guerra': associado.nome_de_guerra,
                        'Tipo': associado.tipo,
                        'Comissao': comissao,
                        'Nome': associado.nome_responsavel,
                        'email': associado.email,
                        'CPF': associado.cpf,
                        'id': associado.id
            }
        
        # cria um certificado de usuário
        file_name, password, error, duration = create_user_certificate(data_dict, password, file_name)
        if not error:
            last_id = tbCertificados.objects.order_by('-id', ).first()
            certificate = tbCertificados.objects.create(
                    data = datetime.today() ,
                    tipo = tbCertificados.TYPE_USER_LEAF,
                    senha = password,
                    arquivo = file_name,
                    validade = datetime.today() + timedelta(days=duration * 365),
                    situacao = tbCertificados.STATUS_VALIDO,
            ).save()

            return last_id.id + 1
    else:
        return cert_id

    return 0


def intall_root_certificate_and_check_validity():
    """
        This function install the root and intermediate certificates, checking the validity and canceling expired certificates.
    """

    certificados = tbCertificados.objects.filter(
        situacao=tbCertificados.STATUS_VALIDO
    )

    validate_root = [certificado.validade  for certificado in certificados if certificado.tipo == tbCertificados.TYPE_ROOT_CA]
    validate_intermediate = [certificado.validade  for certificado in certificados if certificado.tipo == tbCertificados.TYPE_INTERMEDIATE_CA]

    criar_root = False 

    if not validate_root or (validate_root and validate_root[0] <= datetime.today().date()):
        criar_root = True 
    
    elif not validate_intermediate or  (validate_intermediate and validate_intermediate[0] <= datetime.today().date()):
        criar_root = True

    if criar_root:
        # atualizado o root existente para vencido, se existir
        tbCertificados.objects.filter(
                situacao=tbCertificados.STATUS_VALIDO,
                tipo = tbCertificados.TYPE_ROOT_CA,
            ).update(situacao=tbCertificados.STATUS_VENCIDO)
        
        tbCertificados.objects.filter(
                situacao=tbCertificados.STATUS_VALIDO,
                tipo = tbCertificados.TYPE_ROOT_CA,
            ).update(situacao=tbCertificados.STATUS_VENCIDO)

        # cria um certificado root
        file_name, password, error, duration = create_root_certificate()
        if not error:
            tbCertificados.objects.create(
                    data = datetime.today() ,
                    tipo = tbCertificados.TYPE_ROOT_CA,
                    senha = password,
                    arquivo = file_name,
                    validade = datetime.today() + timedelta(days=duration * 365),
                    situacao = tbCertificados.STATUS_VALIDO,
            ).save()

        file_name, password, error, duration = create_intermediate_certificate(password, file_name)
        if not error:
            tbCertificados.objects.create(
                data = datetime.today() ,
                tipo = tbCertificados.TYPE_INTERMEDIATE_CA,
                senha = password,
                arquivo = file_name,
                validade = datetime.today() + timedelta(days=duration * 365),
                situacao = tbCertificados.STATUS_VALIDO,
            ).save()

