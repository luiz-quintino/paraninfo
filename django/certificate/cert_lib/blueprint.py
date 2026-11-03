from .__init__ import *
import hashlib
from ecdsa import SigningKey, VerifyingKey
from ecdsa.util import sigdecode_der, sigencode_der
from . import fileheader as fh
from . import cert_parser as cp
import os

def certstore_pem2der(data: str, little_endian=False, padding_left=False) -> bytes:
    if type(data) == bytes:
        data = data.decode(encoding='ISO-8859-1', errors='strict')

    combined = False
    # dcl_empty = False
    cert_border = ['-----BEGIN CERTIFICATE', 'END CERTIFICATE-----']
    dcl_border = ['-----BEGIN DCL', 'END DCL-----']
    dcl_header = 'IssuerName,SerialNumber'

    cert_list = _get_in(cert_border, data)
    dcl_list = _get_in(dcl_border, data)
    if not dcl_list and not cert_list:
        if dcl_header in data:
            dcl_list = [data]
    elif cert_list and dcl_list:
        combined = True

    if dcl_list:
        dcl_list = _split_dcl(dcl_list)
        # if not dcl_list:
        #     dcl_empty = True

    new_data = b''
    if cert_list:
        for item in cert_list:
            cert = cp.CertificateParser(cert_data=item.encode())
            der_cert = cert.get_cert_serialization('der')
            new_data += der_cert + (b'\xff' * (1536 - len(der_cert)))

    if combined:
        new_data += b'\xff' * 1536

    if dcl_list:
        for row in dcl_list:
            new_data += row[0].encode() + (b'\x00' * (64 - len(row[0])))
            endian = 'little' if little_endian else 'big'
            if padding_left:
                new_data += (b'\x00' * (32 - 20)) + int(row[1], 16).to_bytes(20, endian)
            else:
                new_data += int(row[1], 16).to_bytes(20, endian) + (b'\x00' * (32 - 20))

    return new_data


def sign_certstore_dcl(target_name: str, certstore_data: bin, key_data: bin, cert,
                       header_file_name: str, little_endian=False, padding_left=False, psw='') -> bin:
    data = certstore_data.decode(encoding='ISO-8859-1', errors='strict')

    if data:
        new_data = certstore_pem2der(certstore_data, little_endian=little_endian, padding_left=padding_left)

        f = fh.FileHeader(little_endian=little_endian)
        f.set_file_data(new_data)
        f.set_value(target_name, fh.H_TARGET_NAME)

        header_file = header_file_name + '.tmp.header'
        fio.save_file(header_file, f.get_header_bin())
        hdata = sign_file_header(f, key_data, cert, header_file, psw=psw)
        os.remove(header_file)
        return hdata


def _split_dcl(dcl_list: list) -> list:
    delimiter = '\r\n' if '\r\n' in dcl_list[0] else '\n'
    dcl = dcl_list[0].split(delimiter)
    out_list = []
    for item in dcl:
        if '----' not in item and 'issuername' not in item.lower():
            if ';' in item:
                item = item.split(';')
            else:
                item = item.split(';')
            if len(item) == 2:
                out_list.append(item)
    return out_list


def _get_in(border_list: list, data: str) -> list:
    out_list = []
    last_index = 0
    while last_index < len(data):
        if border_list[0] in data[last_index:]:
            begin = data.index(border_list[0], last_index)
            end = data.index(border_list[1], begin) + len(border_list[1])
            out_list.append(data[begin:end])
            last_index = end
        else:
            last_index = len(data)
    return out_list


def sign_file_header(header: fh.FileHeader, key_data: bin, cert, header_file: bin, psw='') -> bin:
    if header.valid_file_size and header.valid_header and header.valid_file_digest and cert.cert_data:
        sign_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value + \
                    chr(0) * header.dcl_field_size[header.header_names.index(fh.H_SIGNING_NAME)]
        uuid = str(time_uuid.TimeUUID.with_timestamp(float(random.randrange(0, 30)) + time_uuid.utctime()))
        uuid = uuid.replace('-', '')[:20] + fh.NODE_ROW_REGION
        key_id = cert.key_id + ('00' * header.dcl_field_size[header.header_names.index(fh.H_SIGNING_KEY_IDENTIFIER)])

        header.set_value(sign_name, fh.H_SIGNING_NAME, fh.TYPE_CHAR)
        header.set_value(uuid, fh.H_UUID, fh.TYPE_HEX)
        header.set_value(key_id, fh.H_SIGNING_KEY_IDENTIFIER, fh.TYPE_HEX)

        sign = sign_data(header.get_header_bin()[:176], key_data, psw)
        header.set_value(sign, fh.H_HEADER_SIGNATURE, fh.TYPE_BIN)

        data = header.get_header_bin() + header.data
        return data
    return b''


def sign_data(data: bin, private_key: bin, psw='') -> bin:
    if psw:
        if type(psw) == str:
            psw = psw.encode()
    else:
        psw = None
    if data and private_key:
        key = serialization.load_pem_private_key(private_key, password=psw, backend=default_backend())
        digest = SHA256.new(data).digest()
        if key.key_size in [1024, 2048, 3072, 4096]:
            sig = key.sign(
                digest,
                padding.PKCS1v15(),
                utils.Prehashed(hashes.SHA256()))
        elif key.key_size in [256, 384, 521]:
            private_key = key.private_bytes(encoding=serialization.Encoding.PEM,
                              format=serialization.PrivateFormat.TraditionalOpenSSL,
                              encryption_algorithm=serialization.NoEncryption(), )
            sig = SigningKey.from_pem(private_key).sign(data, hashfunc=hashlib.sha256, sigencode=sigencode_der)

        return sig
    return False


def get_digest(data):
    try:
        digest = SHA256.new(data)
    except Exception as e:
        digest = None
    return digest


def verify_sig_data(data, pub_pem, sig):
    result = ''
    # Verify using a public key for RSA PKCS1_V1_5
    digest = get_digest(data)
    try:
        signer = PKCS1_v1_5.new(pub_pem)
        if signer.verify(digest, sig):
            return 'Signed using PKCS1_v1_5'
    except Exception as e:
        result = ''

    # Verify using a public key for RSA PSS
    try:
        signer = PKCS1_PSS.new(pub_pem)
        digest = get_digest(data)
        if signer.verify(digest, sig):
            return 'Signed using PKCSPSS'
    except Exception as e:
        result = ''

    # Verify using a public key for ECDSA
    try:
        signer = VerifyingKey.from_pem(pub_pem)
        if signer.verify(sig, data, hashlib.sha256, sigdecode=sigdecode_der):
            return 'Signed using ECDSA key {}'.format(signer.curve.name)
    except Exception as e:
        result = ''

    return result


if __name__ == '__main__':
    pass
