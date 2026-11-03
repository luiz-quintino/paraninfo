from .__init__ import *
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, load_pem_private_key, pkcs12, pkcs7
from . import cert_creator as cc
from . import cert_parser as cp
from django.conf import settings
from pathlib import Path
import os
import re
import uuid


CRL_DISTRIBUTION_POINTS = 'paraninfo.com.br/certificates'
CERTIFICATE_POLICIES = 'paraninfo.com.br/certificates'
AUTHORITY_INFO_ACCESS = 'paraninfo.com.br/certificates'


def create_root_certificate():
    # password = b'\x81\x14R4eWF\x16\xfe\xc7\xe5|\xa9\x82M5\xbf\xea\xda\x05\xf7\xc0a\x9e\xa9b}\n\xb6O\xd2\xa5'
    # if SHA256.new(password.encode()).digest() != root_password:
    #     self.main_window.message_error('A senha não confere')

    new_cert = cc.CertificateBuilder()
    new_cert.subject['commonName'] = 'Paraninfo Autoridade Certificadora Raiz'
    new_cert.subject['countryName'] = 'BR'
    new_cert.subject['localityName'] = 'Belo Horizonte'
    new_cert.subject['stateOrProvinceName'] = 'MG'
    new_cert.subject['organizationName'] = 'Paraninfo.com.br'
    new_cert.subject['organizationalUnitName'] = ''
    new_cert.identification['serial number'] = cc.create_sn(1)
    
    password = cc.create_sn(16)
    new_cert.key_password = str(password)
    key = cc.Keys('ECC', '521')
    new_cert.keys_algorithm['keys'] = key
    new_cert.public_key_obj = key.key_pair.public_key()

    new_cert.basic_constraints['key usage'].append('crl_sign')
    new_cert.basic_constraints['key usage'].append('key_cert_sign')
    # new_cert.basic_constraints['key usage'].append('digital_signature')

    new_cert.validity['duration'] = 10
    new_cert.issuer['certificate cn'] = None

    new_cert.identification['certificatePolicies'] = ['2.16.76.1.1.0,' + CERTIFICATE_POLICIES]
    new_cert.identification['cRLDistributionPoints'] = [CRL_DISTRIBUTION_POINTS]

    result = new_cert.build_certificate()
    if result == 'success':
        file_name = f'cert/{uuid.uuid4()}'
        fio.save_file(file_name + '.pem', new_cert.pem)
        save_keys(file_name, new_cert)

        return file_name, str(password), '', new_cert.validity['duration']

    return '', '', str(result), ''


def save_keys(file_name, new_cert) -> bool:
    try:
        new_cert.keys_algorithm['keys'].psw = new_cert.key_password
        fio.save_file(file_name + '.key', new_cert.keys_algorithm['keys'].get_private_pem())
    except Exception as e:
        return False
    return True

def create_intermediate_certificate(sig_password: str, file_name: str):
    # sig_password_=SHA256.new(str(sig_password).encode()).digest()
    new_cert = cc.CertificateBuilder()
    new_cert.subject['commonName'] = 'Paraninfo Autoridade Certificadora'
    new_cert.subject['countryName'] = 'BR'
    new_cert.subject['localityName'] = 'Belo Horizonte'
    new_cert.subject['stateOrProvinceName'] = 'MG'
    new_cert.subject['organizationName'] = 'Paraninfo.com.br'
    # new_cert.subject['organizationalUnitName'] = 'Certificado Intermediario'

    new_cert.identification['serial number'] = cc.create_sn(
        int(new_cert.identification['serial number size']))
    password = cc.create_sn(16)
    new_cert.key_password = str(password)
    key = cc.Keys('ECC', '256')
    new_cert.keys_algorithm['keys'] = key
    new_cert.public_key_obj = key.key_pair.public_key()

    new_cert.basic_constraints['key usage'].append('key_cert_sign')
    new_cert.basic_constraints['key usage'].append('crl_sign')
    # new_cert.basic_constraints['key usage'].append('digital_signature')

    new_cert.validity['duration'] = 4
    new_cert.issuer['certificate path'] = f'{file_name}.pem'
    new_cert.issuer['secret key path'] = f'{file_name}.key'
    new_cert.load_key_password = sig_password.encode()

    new_cert.identification['authorityInfoAccess'] = ['1.3.6.1.5.5.7.48.2,' + AUTHORITY_INFO_ACCESS]
    new_cert.identification['certificatePolicies'] = ['2.16.76.1.1.0,' + CERTIFICATE_POLICIES]
    new_cert.identification['cRLDistributionPoints'] = [CRL_DISTRIBUTION_POINTS]

    result = new_cert.build_certificate()
    
    if result == 'success':
        file_name = f'cert/{uuid.uuid4()}'
        # fio.save_file(file_name + '.txt', str(password).encode())
        save_keys(file_name, new_cert)

        # cert = cp.CertificateParser(new_cert.pem)
        # cert_root = cp.CertificateParser(fio.open_file('cert/root.pem'))
        # pk7 = pkcs7.serialize_certificates([cert.cert_data, cert_root.cert_data], serialization.Encoding.PEM)
        # file_name = 'cert/root.p7b'
        # file_name = 'cert/user.pem'

        fio.save_file(file_name + '.pem', new_cert.pem)
        return file_name, str(password), '', new_cert.validity['duration']

    return '', '', str(result), '' 


def titlle_str(text: str) -> str:
    texts = text.split(' ')
    text_out = []
    for text in texts:
        if len(text) > 3 or len(text) == 1 or text.upper() in ['R.', 'AV.', 'AV', 'BR', 'BH', 'MG', 'SP', 'ANA',
                                                                'NEY', 'ARY']:
            text_out.append(text[0].upper() + text[1:].lower())
        else:
            text_out.append(text.lower())
    return ' '.join(text_out)


# def create_certificate_tesoureiro(data_dict: dict, sig_password: bytes, file_name: str) -> str:
#     new_cert = cc.CertificateBuilder()
#     nasc1 = '{2}{1}{0}'.format(*data_dict['Nascimento'].split()[0].split('-'))
#     new_cert.subject['countryName'] = 'BR'
#     new_cert.subject['localityName'] = 'Belo Horizonte'
#     new_cert.subject['stateOrProvinceName'] = 'MG'
#     new_cert.subject['organizationalUnitName 2'] = str(data_dict['Código associado'])
#     new_cert.subject['organizationalUnitName 1'] = 'AL ' + titlle_str(data_dict['Nome de guerra'])
#     new_cert.subject['organizationalUnitName'] = data_dict['Tipo']
#     new_cert.subject['organizationName'] = str(data_dict['Comissao'])
#     new_cert.subject['commonName'] = titlle_str(data_dict['Nome'])

#     new_cert.identification['serial number'] = cc.create_sn(20)
#     password = cc.create_sn(3)
#     new_cert.key_password = str(password)
#     key = cc.Keys('ECC', '256')
#     new_cert.keys_algorithm['keys'] = key
#     new_cert.public_key_obj = key.key_pair.public_key()

#     new_cert.basic_constraints['key usage'].append('digital_signature')
#     new_cert.basic_constraints['key usage'].append('content_commitment')
#     new_cert.basic_constraints['key usage'].append('key_encipherment')
#     new_cert.basic_constraints['extended key'].append('clientAuth')
#     new_cert.basic_constraints['extended key'].append('serverAuth')
#     new_cert.basic_constraints['extended key'].append('emailProtection')
#     new_cert.alternative_name = ['email:' + data_dict['email'] + ',',
#                                     'otherName:2.16.76.1.3.1,' + nasc1,
#                                     'otherName:2.16.76.1.3.9,' + data_dict['CPF']]

#     new_cert.validity['duration'] = 1
#     new_cert.issuer['certificate path'] = f'cert/{file_name}.pem'
#     new_cert.issuer['secret key path'] = f'cert/{file_name}.key'
#     new_cert.load_key_password = sig_password.decode()

#     new_cert.identification['authorityInfoAccess'] = ['1.3.6.1.5.5.7.48.2,' + AUTHORITY_INFO_ACCESS]
#     new_cert.identification['certificatePolicies'] = ['2.16.76.1.1.0,' + CERTIFICATE_POLICIES]
#     new_cert.identification['cRLDistributionPoints'] = [CRL_DISTRIBUTION_POINTS]

#     new_cert.basic_constraints['basic constraints'] = False
#     new_cert.basic_constraints['include basic constraints'] = False

#     result = new_cert.build_certificate()
#     if result == 'success':
#         file_name = 'cert/{}_Ct'.format(titlle_str(data_dict['Nome de guerra']))
#         fio.save_file(file_name + '.pem', new_cert.pem)
#         if save_keys(file_name, new_cert):
#             fio.save_file(file_name + '.txt', str(password).encode())
#             key = load_pem_private_key(fio.open_file(file_name + '.key'), str(password).encode(),
#                                         backend=default_backend())
#             cert = cp.CertificateParser(new_cert.pem)
#             cert_inter = cp.CertificateParser(fio.open_file(new_cert.issuer['certificate path']))
#             cert_root = cp.CertificateParser(fio.open_file('cert/root.pem'))
#             p12 = pkcs12.serialize_key_and_certificates(b"Comissao de Formatura",
#                                                         key,
#                                                         cert.cert_data,
#                                                         [cert_inter.cert_data, cert_root.cert_data],
#                                                         BestAvailableEncryption(str(password).encode()))

#             fio.save_file(file_name + '.pfx', p12)
#             file_name = f'{titlle_str(data_dict['Nome de guerra'])}_Ct.pem'
#             fio.save_file(file_name, new_cert.pem)
#             # return hex(new_cert.identification['serial number'])[2:]
#             return file_name, '', ''
        
#     return '','', str(result), ''

def create_user_certificate(data_dict: dict, sig_password: bytes, file_name: str) -> list:
    new_cert = cc.CertificateBuilder()
    nasc1 = '{2}{1}{0}'.format(*data_dict['Nascimento'].split()[0].split('-'))
    new_cert.subject['countryName'] = 'BR'
    new_cert.subject['localityName'] = 'Belo Horizonte'
    new_cert.subject['stateOrProvinceName'] = 'MG'
    new_cert.subject['organizationalUnitName 2'] = str(data_dict['Código associado'])
    new_cert.subject['organizationalUnitName 1'] = 'AL ' + titlle_str(data_dict['Nome de guerra'])
    new_cert.subject['organizationalUnitName'] = data_dict['Tipo']
    new_cert.subject['organizationName'] = str(data_dict['Comissao'])
    new_cert.subject['commonName'] = titlle_str(data_dict['Nome'])

    new_cert.identification['serial number'] = cc.create_sn(20)
    password = cc.create_sn(16)
    new_cert.key_password = str(password)
    key = cc.Keys('ECC', '256')
    new_cert.keys_algorithm['keys'] = key
    new_cert.public_key_obj = key.key_pair.public_key()

    new_cert.basic_constraints['key usage'].append('digital_signature')
    new_cert.basic_constraints['key usage'].append('content_commitment')
    new_cert.basic_constraints['key usage'].append('key_encipherment')
    new_cert.basic_constraints['extended key'].append('clientAuth')
    new_cert.basic_constraints['extended key'].append('serverAuth')
    new_cert.basic_constraints['extended key'].append('emailProtection')
    new_cert.alternative_name = ['email:' + data_dict['email'] + ',',
                                    'otherName:2.16.76.1.3.1,' + nasc1,
                                    'otherName:2.16.76.1.3.9,' + data_dict['CPF']]

    new_cert.validity['duration'] = 1
    new_cert.issuer['certificate path'] = f'{file_name}.pem'
    new_cert.issuer['secret key path'] = f'{file_name}.key'
    new_cert.load_key_password = sig_password

    new_cert.identification['authorityInfoAccess'] = ['1.3.6.1.5.5.7.48.2,' + AUTHORITY_INFO_ACCESS]
    new_cert.identification['certificatePolicies'] = ['2.16.76.1.1.0,' + CERTIFICATE_POLICIES]
    new_cert.identification['cRLDistributionPoints'] = [CRL_DISTRIBUTION_POINTS]

    new_cert.basic_constraints['basic constraints'] = False
    new_cert.basic_constraints['include basic constraints'] = True

    result = new_cert.build_certificate()
    if result == 'success':
        file_name = f'cert/{uuid.uuid4()}'
        fio.save_file(file_name + '.pem', new_cert.pem)
        save_keys(file_name, new_cert)
        return file_name, password, '', new_cert.validity['duration']

    return '','',str(result), ''