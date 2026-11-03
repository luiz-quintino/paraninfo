from django.shortcuts import render

from .cert_lib.sign_document import sign_pdf

from django.conf import settings
from pathlib import Path
from certificate.models import tbCertificados
from datetime import datetime, timedelta
from .cert_lib.sign_document import install_user_certificate_and_check_validity

def certificate(request):
    # TODO criar página para mostrar os certificados
    id = install_user_certificate_and_check_validity()

    file_pdf = 'cert/2026-AGOSTO-livro caixa.pdf' 
    cert = tbCertificados.objects.filter(id=id).first()
    cert_root = tbCertificados.objects.filter(
            situacao=tbCertificados.STATUS_VALIDO,
            tipo=tbCertificados.TYPE_ROOT_CA
        ).first()
    cert_intermediate = tbCertificados.objects.filter(
                situacao=tbCertificados.STATUS_VALIDO,
                tipo=tbCertificados.TYPE_INTERMEDIATE_CA
            ).first()
    
    file_root = cert_root.arquivo + '.pem'
    file_intermediate = cert_intermediate.arquivo + '.pem'


    file_cert = f'{cert.arquivo}.pem'
    file_key = f'{cert.arquivo}.key'
    password = cert.senha
    sign_pdf(file_name=file_pdf, key_file=file_key,password= password, cert_file= file_cert, cert_chain=[file_root, file_intermediate])

    return render(request, 'home.html', {})

def _test_certificate_creation(request):
    absolute_folder = Path(settings.BASE_DIR / 'cert')
    absolute_folder.mkdir(parents=True, exist_ok=True)
    a=create_root_certificate()
    print(a)

    b=create_intermediate_certificate(a[1])
    print(b)

    data_dict ={
                'Nascimento': '1973-10-04',
                'Código associado': '3004',
                'Nome de guerra': 'Quintino',
                'Tipo': 'Teseoureiro',
                'Comissao': 'Minha comissão',
                'Nome': 'Luiz Quintino',
                'email': 'luiz.quintino@gmail.com',
                'CPF': '88422070934',
                'id': '2'
    }
    c=create_user_certificate(data_dict, b[1])
    print(c)

    file_pdf = 'cert/2026-AGOSTO-livro caixa.pdf' 
    file_cert = f'{c[0]}.pem'
    file_key = f'{c[0]}.key'
    password = c[1]
    sign_pdf(file_pdf, file_key, password, file_cert, [])

    return render(request, 'home.html', {})


# def get_certificate_to_signature(id):
#     certificado = tbCertificados.objects.filter(
#                     id=id,
#                 ).first()
    
#     validate_user = certificado.validade

# def intall_user_certificate_and_check_validity(id=None):
#     """
#         This function install user certificates.
#     """
#     validate_user = datetime.today().date()

#     if id:
#         certificado = tbCertificados.objects.filter(
#                 id=id,
#             ).first()
#         validate_user = certificado.validade
    
#     if validate_user <= datetime.today().date():
#         # atualizado o user existente para vencido, se existir
#         if id:
#             tbCertificados.objects.filter(
#                     id=id,
#                 ).update(situacao=tbCertificados.STATUS_VENCIDO)
        
#         intermediate = tbCertificados.objects.filter(
#                 situacao=tbCertificados.STATUS_VALIDO,
#                 tipo = tbCertificados.TYPE_INTERMEDIATE_CA,
#             ).first()

#         password = intermediate.senha
#         file_name = intermediate.arquivo
#         data_dict = {
#                         'Nascimento': '1973-10-04',
#                         'Código associado': '3004',
#                         'Nome de guerra': 'Quintino',
#                         'Tipo': 'Teseoureiro',
#                         'Comissao': 'Minha comissão',
#                         'Nome': 'Luiz Quintino',
#                         'email': 'luiz.quintino@gmail.com',
#                         'CPF': '88422070934',
#                         'id': '2'
#             }
        
#         # cria um certificado de usuário
#         file_name, password, error, duration = create_user_certificate(data_dict, password, file_name)
#         if not error:
#             last_id = tbCertificados.objects.order_by('-id', ).first()
#             certificate = tbCertificados.objects.create(
#                     data = datetime.today() ,
#                     tipo = tbCertificados.TYPE_USER_LEAF,
#                     senha = password,
#                     arquivo = file_name,
#                     validade = datetime.today() + timedelta(days=duration * 365),
#                     situacao = tbCertificados.STATUS_VALIDO,
#             ).save()

#             return last_id.id + 1
#     else:
#         return id

#     return 0


# def intall_root_certificate_and_check_validity():
#     """
#         This function install the root and intermediate certificates, checking the validity and canceling expired certificates.
#     """

#     certificados = tbCertificados.objects.filter(
#         situacao=tbCertificados.STATUS_VALIDO
#     )

#     validate_root = [certificado.validade  for certificado in certificados if certificado.tipo == tbCertificados.TYPE_ROOT_CA]
#     validate_intermediate = [certificado.validade  for certificado in certificados if certificado.tipo == tbCertificados.TYPE_INTERMEDIATE_CA]

#     criar_root = False 

#     if not validate_root or (validate_root and validate_root[0] <= datetime.today().date()):
#         criar_root = True 
    
#     elif not validate_intermediate or  (validate_intermediate and validate_intermediate[0] <= datetime.today().date()):
#         criar_root = True

#     if criar_root:
#         # atualizado o root existente para vencido, se existir
#         tbCertificados.objects.filter(
#                 situacao=tbCertificados.STATUS_VALIDO,
#                 tipo = tbCertificados.TYPE_ROOT_CA,
#             ).update(situacao=tbCertificados.STATUS_VENCIDO)
        
#         tbCertificados.objects.filter(
#                 situacao=tbCertificados.STATUS_VALIDO,
#                 tipo = tbCertificados.TYPE_ROOT_CA,
#             ).update(situacao=tbCertificados.STATUS_VENCIDO)

#         # cria um certificado root
#         file_name, password, error, duration = create_root_certificate()
#         if not error:
#             tbCertificados.objects.create(
#                     data = datetime.today() ,
#                     tipo = tbCertificados.TYPE_ROOT_CA,
#                     senha = password,
#                     arquivo = file_name,
#                     validade = datetime.today() + timedelta(days=duration * 365),
#                     situacao = tbCertificados.STATUS_VALIDO,
#             ).save()

#         file_name, password, error, duration = create_intermediate_certificate(password, file_name)
#         if not error:
#             tbCertificados.objects.create(
#                 data = datetime.today() ,
#                 tipo = tbCertificados.TYPE_INTERMEDIATE_CA,
#                 senha = password,
#                 arquivo = file_name,
#                 validade = datetime.today() + timedelta(days=duration * 365),
#                 situacao = tbCertificados.STATUS_VALIDO,
#             ).save()


