from .__init__ import *
import hashlib
import string
import Crypto.PublicKey.ECC as ECC
from ecdsa import SigningKey, VerifyingKey, NIST256p, NIST384p, NIST521p
from ecdsa.util import sigdecode_der
from cryptography.x509.oid import ObjectIdentifier
from cryptography.hazmat.primitives.serialization import pkcs7
from . import blueprint as bp
from . import cert_parser as cp

raise_error = False  # Set to False to ignore errors and True to raise errors

KEY_USAGE = {
    '1.3.6.1.4.1.29858.3.1.2.1': 'Bootloader',
    '1.3.6.1.4.1.29858.3.1.2.3': 'Firmware',
    '1.3.6.1.4.1.29858.3.1.2.4': 'Calibration',
    '1.3.6.1.4.1.29858.3.1.2.5': 'certStore and DCL',
    '1.3.6.1.4.1.29858.3.1.2.12': 'HTA Firmware',
    '1.3.6.1.4.1.29858.3.1.2.13': 'coProcFirmware',
    '1.3.6.1.4.1.29858.3.1.2.14': 'coHostedApp',
    '1.3.6.1.4.1.29858.3.1.2.15': 'coHostedConfig',
    '1.3.6.1.4.1.29858.3.1.2.16': 'Map (entertainment scope only)',
    '1.3.6.1.4.1.29858.3.1.2.17': 'Forensic Firmware',
    '1.3.6.1.4.1.29858.3.1.2.18': 'SAM',
    '1.3.6.1.4.1.29858.3.1.2.19': 'Inventory',
    '1.3.6.1.4.1.29858.3.1.1.1': 'Authenticated Diagnostic Access',
    '1.3.6.1.4.1.29858.3.2.1.2': 'targetName',
    '1.3.6.1.4.1.29858.3.2.1.1': 'Authorized Role',
    '1.3.6.1.4.1.311.21.1': 'Authorized Role API (*)',
    '1.3.6.1.4.1.29858.3.2.1.3': 'Auth Role Group',
    '1.3.6.1.4.1.29858.3.2.1.4': 'Auth Role Text',
    '1.3.6.1.4.1.29858.3.2.1.5': 'ECU Target Detail',
    '2.16.76.1.2.1.38': 'Identificador de Política',

    # ICP-Brasil (PKI Brazil)
    '2.16.76.1.3.1': 'dados-pf',
    '2.16.76.1.3.2': 'Nome PJ',
    '2.16.76.1.3.3': 'cnpj',
    '2.16.76.1.3.4': 'dados-pj',
    '2.16.76.1.3.5': 'titulo-eleitor-pf',
    '2.16.76.1.3.6': 'cei-pf',
    '2.16.76.1.3.7': 'cei-pj',
    '2.16.76.1.3.8': 'nome-cnpj',
    '2.16.76.1.3.9': 'ric',
    '2.16.76.1.3.10': 'a-cf-e-sat-othername',

}

AUTHORIZED_ROLE = {
    0: 'Engineer',
    1: 'Workshop Operator Online (e.g. Dealer Servicing or SeRMI enabled 3rd party Servicing '
       'using an official FCA tool suite)',
    2: 'Manufacturing (aka Assembly Plant)',
    3: 'Supplier (e.g. Tier-1 supplier of the ECU)',
    4: 'After-Market (e.g. upfitters – not servicing workshops)',
    5: 'On-Board Tool (e.g. other ECUs initiating UDS)',
    6: 'Workshop Operator Offline',
    7: 'Independent Workshop Operator Online (e.g. Non-SeRMI enable 3rd party Servicing using '
       'an official FCA tool suite such as wiTECH2.0)',
    8: 'Independent Workshop Operator Pass-through Online (e.g. 3rd party Servicing using '
       'FCA J2534 middleware or other non-FCA, 3rd party tool)',
    9: 'FOTA',

}


class CertificateParser:
    """A certificate parser that reads PEM and DER certificates from a given bin_data"""
    SIGNATURE_RSA = 2
    SIGNATURE_ECDSA = 1

    SIGN_TYPE = {0: '',
                 1: 'Signed using PKCS1_v1_5',
                 2: 'Signed using PKCS1_PSS',
                 3: 'Signed using ECDSA',
                 }

    def __init__(self, cert_data: bin):
        self.cert_data = None
        self.public_key = None
        self.sig = None
        self.sig_hash = None
        self.is_ca = False
        self.auth_issuer = None
        self.issuer = None
        self.auth_sn = None
        self.auth_key_id = None
        self.auth_info_access = None
        self.sn = None
        self.subject = None
        self.key_id = None
        self.parsed = None
        self.common_name = None
        self.target_name = None
        '''The certificate target'''
        self.target_name_oid = None
        self.extended_key_usage_oid = None
        self.error = []
        self.key_type = None
        self.key_size = None
        self.info = {
            'sn': None,
            'cn': None,
            'kind': None,  # {kinds: ['Root', 'CA', 'Leaf']}
            'validity': None,
            'validity_duration': None,
            'key_type': None,
            'key_size': None,
            'sig_type': None,
            'version': None,
            'subject': [],
            'issuer': [],
            'basicConstraints': {},
            'keyUsage': {},
            'extendedKeyUsage': {},
            'authority': [],
            'oids': []
        }

        if cert_data:
            self.parsed = self.parser_certificate(cert_data)
        else:
            raise Exception('Missing certificate')

    def is_valid_signature(self, cert_pem: str) -> bool:
        # Verify if the certificate is correctly signed
        if cert_pem:
            return self.validate_sign(pem=cert_pem, sig=self.sig, data=self.tbs)
        elif (self.auth_sn == self.sn) and (self.sn is not None):
            return self.validate_sign(pem=self.get_cert_serialization(), sig=self.sig, data=self.tbs)
        return False

    def get_cert_serialization(self, cert_type='PEM'):
        if cert_type == 'PEM':
            cert_data = self.cert_data.public_bytes(encoding=serialization.Encoding.PEM)
        else:
            cert_data = self.cert_data.public_bytes(encoding=serialization.Encoding.DER)

        return cert_data

    def get_cert_decoded_pem(self) -> str:
        if self.error:
            return self.error
        return self.get_cert_serialization().decode(encoding='ISO-8859-1', errors='strict')

    def _extract_cert(self, cert_data) -> x509.Certificate:
        cert = ''
        try:
            if cert_data.startswith(b'-----BEGIN CERTIFICATE'):
                # PEM
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            elif cert_data.startswith(b'-----BEGIN PKCS7'):
                cert = pkcs7.load_pem_pkcs7_certificates(cert_data)[-1]
            else:
                # DER
                try:
                    cert = x509.load_der_x509_certificate(cert_data, default_backend())
                except:
                    try:
                        cert = pkcs7.load_der_pkcs7_certificates(cert_data)[-1]
                    except:
                        pass
        except Exception as e:
            if raise_error:
                return ''
            self.error.append('Wrong or invalid certificate format.')
            return ''
        return cert

    def parser_certificate(self, cert_data: bin) -> str:
        if self.error:
            return self.error

        cert_ob = self._extract_cert(cert_data)
        if not cert_ob:
            return ''

        parce_cert = ''
        self.cert_data = cert_ob
        # tbs is the signed part of the certificate
        self.tbs = cert_ob.tbs_certificate_bytes
        parce_cert += '\n' + 'Version: ' + str(cert_ob.version.name)
        self.info['version'] = str(cert_ob.version.name)
        parce_cert += '\n' + 'Serial number: ' + hex(cert_ob.serial_number)[2:]
        self.info['sn'] = hex(cert_ob.serial_number)[2:]
        self.sn = cert_ob.serial_number
        # parce_cert += '\n' +  'public private_key ' + str(cert_signer.public_key())
        # self.public_key = cert_ob.public_key()
        cert_type = 'not know'
        self.sig_hash = cert_ob.signature_hash_algorithm.name
        self.key_size = cert_ob.public_key().key_size
        if self.key_size in [160, 256, 384, 521]:
            cert_type = cert_ob.public_key().curve.name #+ ' ' + ECC.import_key(cert_data).curve
            a = cert_ob.public_key().public_numbers().x.to_bytes(round(self.key_size / 8 + .5), 'big').hex(':', 1)
            a += ':' + cert_ob.public_key().public_numbers().y.to_bytes(round(self.key_size / 8 + .5), 'big').hex(':',
                                                                                                                  1)
            self.key_type = self.SIGNATURE_ECDSA
        elif self.key_size in [1024, 2048, 3072, 4096]:
            cert_type = 'rsaEncryption'
            a = cert_ob.public_key().public_numbers().n.to_bytes(self.key_size // 8, 'big').hex(':', 1)
            self.key_type = self.SIGNATURE_RSA
        else:
            return ''

        self.info['key_size'] = self.key_size
        self.info['key_type'] = cert_type

        # parce_cert += '\n' + 'exponent: ' + str(cert_ob.public_key().public_numbers().e)
        self.issuer = cert_ob.issuer
        parce_cert += '\n' + 'Subject: ' + str(cert_ob.subject.rfc4514_string())
        parce_cert += '\n' + 'Issuer: ' + str(cert_ob.issuer.rfc4514_string())
        parce_cert += '\n' + 'Validity: from {} to {}'.format(str(cert_ob.not_valid_before),
                                                              str(cert_ob.not_valid_after))
        parce_cert += '\n' + 'Public-key Algorithm: {} ({} bit)'.format(cert_type, self.key_size)
        parce_cert += '\n' + 'Sig alg oid: {} {}'.format(cert_ob.signature_algorithm_oid.dotted_string,
                                                         cert_ob.signature_algorithm_oid._name)

        self.subject = cert_ob.subject
        self.common_name = cert_ob.subject.get_attributes_for_oid(oid=NameOID.COMMON_NAME)[0].value

        self.info['sig_type'] = cert_ob.signature_algorithm_oid._name
        # self.info['oids'].append({cert_ob.signature_algorithm_oid.dotted_string: cert_ob.signature_algorithm_oid._name})
        self.info['validity'] = 'from {} to {}'.format(str(cert_ob.not_valid_before), str(cert_ob.not_valid_after))

        if (cert_ob.not_valid_after.date() - cert_ob.not_valid_before.date()).days // 365 < 0:
            validity_duration = '{} days'.format((cert_ob.not_valid_after.date()
                                                  - cert_ob.not_valid_before.date()).days // 30)
        else:
            validity_duration = '{} years'.format((cert_ob.not_valid_after.date()
                                                   - cert_ob.not_valid_before.date()).days // 365)
        self.info['validity_duration'] = validity_duration
        self.info['cn'] = self.common_name
        # parce_cert += '\n' + 'Subject public_bytes: ' + str(cert_ob.subject.rfc4514_string())
        # parce_cert += '\n' + 'Sig hash alg: ' + str(cert_ob.signature_hash_algorithm.name)

        for obj in cert_ob.subject.rdns:
            for attribute in obj._attributes:
                self.info['subject'].append({attribute.oid.dotted_string:
                                                 {'name': attribute.oid._name, 'value': attribute.value}})
        for obj in cert_ob.issuer.rdns:
            for attribute in obj._attributes:
                self.info['issuer'].append({attribute.oid.dotted_string:
                                                {'name': attribute.oid._name, 'value': attribute.value}})

        parce_cert += '\n\n' + 'Extensions'
        for item in cert_ob.extensions:
            # parce_cert += '\n' +  str(item)
            if item.oid.dotted_string in KEY_USAGE.keys():
                parce_cert += '\n' + '   ' + item.oid.dotted_string + ' ' + KEY_USAGE.get(item.oid.dotted_string)
            else:
                parce_cert += '\n' + '   ' + (item.oid.dotted_string) + ' ' + item.oid._name

            parce_cert += '\n      critical=' + str(item.critical)
            if item.oid._name == 'basicConstraints':
                self.is_ca = item.value.ca
                parce_cert += '\n      CA=' + str(self.is_ca)
                parce_cert += '\n      path length=' + str(item.value.path_length)

                self.info['basicConstraints'] = {'critical': item.critical,
                                                 'ca': item.value.ca,
                                                 'path_length': item.value.path_length}

                self.info['oids'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                   'critical': item.critical,
                                                                   'ca': item.value.ca,
                                                                   'path_length': item.value.path_length}})

            elif item.oid._name == 'authorityKeyIdentifier':
                values = []
                if item.value.key_identifier:
                    self.auth_key_id = item.value.key_identifier.hex()
                    parce_cert += '\n      auth_key_id: ' + self.auth_key_id
                    values.append({'key_identifier': self.auth_key_id})
                if item.value.authority_cert_serial_number:
                    self.auth_sn = item.value.authority_cert_serial_number
                    parce_cert += '\n      auth_sn: ' + hex(self.auth_sn)[2:]
                    values.append({'authority_cert_serial_number': hex(self.auth_sn)[2:]})
                if item.value.authority_cert_issuer:
                    self.auth_issuer = item.value.authority_cert_issuer[0].value.rfc4514_string()
                    parce_cert += '\n      auth_issuer: ' + self.auth_issuer
                    values.append({'authority_cert_issuer': self.auth_issuer})

                self.info['authority'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                        'critical': item.critical,
                                                                        'values': values}})

            elif item.oid._name == 'keyUsage':
                for usage, value in item.value.__dict__.items():
                    if value:
                        parce_cert += '\n      ' + usage[1:] + '=True'

                self.info['keyUsage'] = {'critical': item.critical,
                                         'values': item.value.__dict__.items()}
                self.info['oids'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                   'critical': item.critical,
                                                                   'values': self._get_true_values(
                                                                       item.value.__dict__.items())}})

            elif item.oid._name == 'extendedKeyUsage':
                values = []
                for usage, value in item.value.__dict__.items():
                    self.extended_key_usage_oid = KEY_USAGE.get(value[0].dotted_string)
                    if not self.extended_key_usage_oid:
                        self.extended_key_usage_oid = ObjectIdentifier(value[0].dotted_string)._name
                    parce_cert += '\n      ' + str(value[0].dotted_string) + ' ' + self.extended_key_usage_oid
                    values.append({value[0].dotted_string: self.extended_key_usage_oid})

                self.info['extendedKeyUsage'] = {'critical': item.critical, 'values': values}
                self.info['oids'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                   'critical': item.critical,
                                                                   'values': values}})

            elif item.oid._name == 'subjectKeyIdentifier':
                self.key_id = item.value.digest.hex()
                parce_cert += '\n' + '      key_id: ' + (item.value.digest.hex())

                self.info['oids'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                   'critical': item.critical,
                                                                   'values': item.value.digest.hex()}})

            elif item.oid._name == 'Unknown OID' \
                    and (KEY_USAGE.get(item.oid.dotted_string) == 'Authorized Role'
                         or KEY_USAGE.get(item.oid.dotted_string) == 'targetName'
                         or KEY_USAGE.get(item.oid.dotted_string) == 'Auth Role Group'):

                values = []
                for usage, value in item.value.__dict__.items():
                    if type(value) is bytes:
                        try:
                            item_s = str(value[2:].decode(encoding='ISO-8859-1', errors='strict'))
                            item_name = ''
                            for s in item_s:
                                if s in string.printable:
                                    item_name += s
                        except:
                            item_name = ''

                        if KEY_USAGE.get(item.oid.dotted_string) == 'Authorized Role':
                            item_name = AUTHORIZED_ROLE.get(value[-1])

                        elif KEY_USAGE.get(item.oid.dotted_string) == 'targetName':
                            self.target_name = item_name
                            self.target_name_oid = item.oid.dotted_string

                        parce_cert += '\n      {} (0x{})'.format(item_name, value.hex())

                        if KEY_USAGE.get(item.oid.dotted_string) == 'Auth Role Group':
                            s = '\n        Authorized Role Group: '
                            for key, role in AUTHORIZED_ROLE.items():
                                if len(item_name) > key:
                                    if item_name[-(key + 1)] == '1':
                                        s += '\n          ' + role.split('(')[0]
                            parce_cert += s

                        values.append({item.oid.dotted_string: [item_name, value.hex()]})

                self.info['oids'].append({item.oid.dotted_string: {'name': KEY_USAGE.get(item.oid.dotted_string),
                                                                   'critical': item.critical,
                                                                   'values': values}})

            elif item.oid._name == 'cRLDistributionPoints' or \
                    item.oid._name == 'certificatePolicies' or \
                    item.oid._name == 'Unknown OID' or \
                    item.oid._name == 'authorityInfoAccess':
                value = ''
                for usage, values in item.value.__dict__.items():
                    # print(values)
                    value += self._get_value(values)

                self.info['oids'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                   'critical': item.critical,
                                                                   'values': value}})
                parce_cert += value

            elif item.oid._name == 'subjectAltName':
                for usage, value in item.value.__dict__.items():
                    parce_cert += self._get_value(value)
            else:
                parce_cert += '\n' + '      ' + str(item.value)

                self.info['oids'].append({item.oid.dotted_string: {'name': item.oid._name,
                                                                   'critical': item.critical,
                                                                   'values': item.__dict__.items()}})

            parce_cert += '\n'

        if str(cert_ob.subject.rfc4514_string()) == str(cert_ob.issuer.rfc4514_string()):
            self.info['kind'] = 'Root'
        elif self.info['basicConstraints']:
            self.info['kind'] = 'CA' if self.info['basicConstraints']['ca'] else 'Leaf'
        else:
            self.info['kind'] = 'Leaf'

        self.public_key = bytes.fromhex(a.replace(':', ''))

        a = [a[i:i + 45] for i in range(0, len(a), 45)]
        parce_cert += '\n' + 'Public key: '
        for b in a:
            parce_cert += '\n' + '   ' + b

        self.sig = cert_ob.signature
        a = cert_ob.signature.hex(':', 1)
        a = [a[i:i + 54] for i in range(0, len(a), 54)]
        parce_cert += '\n' + 'Signature Algoritm:'
        for b in a:
            parce_cert += '\n' + '   ' + b

        return parce_cert

    def _get_true_values(self, items) -> dict:
        result = {}
        for item, value in items:
            if value:
                result[item.strip('_')] = value
        return result

    def _get_value(self, values, spc=1) -> str:
        value = ''
        if type(values).__name__ == 'dict_items':
            values = dict(values)

        if type(values).__name__ == 'ObjectIdentifier':
            oid_name = KEY_USAGE.get(values.dotted_string)
            if not oid_name:
                oid_name = ObjectIdentifier(values.dotted_string)._name
            value += '\n{}{} {}'.format(2 * spc * ' ', values.dotted_string, oid_name)

        elif type(values).__name__ == 'GeneralNames':
            for item in values:
                if type(item).__name__ == 'OtherName':
                    oid_name = KEY_USAGE.get(item._type_id.dotted_string)
                    if not oid_name:
                        oid_name = ObjectIdentifier(item._type_id.dotted_string)._name
                    size = int(item._value[1:2].hex(), 16)
                    item_decode = item._value[2:size+2].decode(encoding='ISO-8859-1', errors='strict')
                    value += '\n{}{} {}: {}'.format(6 * spc * ' ', item._type_id.dotted_string, oid_name, item_decode)
                elif type(item).__name__ == 'RFC822Name':
                    value += '\n{}{}: {}'.format(6 * spc * ' ', 'email', item._value)
                else:
                    value += '\n{}{}: {}'.format(6 * spc * ' ', type(item).__name__, item._value)

        elif type(values) == dict:
            for key, item in values.items():
                value += '\n{}{}: {}'.format(2 * spc * ' ', key.strip('_').strip(), self._get_value(item, spc + 1))

        elif type(values) == list:
            for item in values:
                value += '{}{}'.format(1 * spc * ' ', self._get_value(item, spc + 1))

        elif type(values) == bytes:
            converted_value = ''
            try:
                item_s = str(values[2:].decode(encoding='ISO-8859-1', errors='strict'))
                for s in item_s:
                    if 31 > ord(s) > 127:
                        converted_value += s
                if len(converted_value) > (len(value) * 0.7):
                    value += converted_value
                else:
                    value += '\n0x' + values.hex()
            except:
                value += '\n0x' + values.hex()

        elif type(values) == int:
            value += '\n' + str(values)

        elif type(values) == str:

            value += '"{}"'.format(values.strip('_').strip())

        else:
            if values:
                try:
                    dict_value = values.__dict__.items()
                    value += '\n {}{}: '.format(1 * spc * ' ', type(values).__name__)
                except:
                    dict_value += '<.>'

                value += self._get_value(dict_value, spc + 1)
            else:
                value += 'None'

        return value

    def validate_sign(self, pem, sig, digest=None, data=None) -> bool:
        # Manually verify the certificate signature
        cert = cp.CertificateParser(pem)

        cert.get_verify(sig, data, cert.sig_hash)
        try:
            signer = PKCS1_v1_5.new(RSA.importKey(pem))
            if not digest:
                digest = SHA256.new(data)
            return signer.verify(digest, sig)
        except Exception as e:
            return False

    def get_signer(self):
        if self.key_type == self.SIGNATURE_RSA:
            return [PKCS1_v1_5.new(RSA.importKey(self.get_cert_serialization())),
                    PKCS1_PSS.new(RSA.importKey(self.get_cert_serialization()))]
        elif self.key_type == self.SIGNATURE_ECDSA:
            keys = {256: NIST256p, 382: NIST384p, 521: NIST521p}
            key_size = keys.get(self.key_size)
            return VerifyingKey.from_string(self.public_key, validate_point=False, curve=key_size)

    def get_verify(self, sig, data, sha='sha256', cert_pem='') -> str:
        if cert_pem.key_size > 1000:
            pub_pem = RSA.importKey(cert_pem.get_cert_decoded_pem())
        else:
            pub_pem = cert_pem._extract_cert(cert_pem.get_cert_decoded_pem().encode()).public_key(). \
                public_bytes(encoding=serialization.Encoding.PEM,
                             format=serialization.PublicFormat.SubjectPublicKeyInfo)

        result = bp.verify_sig_data(data, pub_pem, sig)
        return result

        result = 0

        try:
            digest = SHA256.new(data)
            hash_lib = hashlib.sha256

            if sha == 'sha384':
                digest = SHA384.new(data)
                hash_lib = hashlib.sha384
            elif sha == 'sha512':
                digest = SHA512.new(data)
                hash_lib = hashlib.sha512
            elif sha == 'sha224':
                digest = SHA224.new(data)
                hash_lib = hashlib.sha224
            elif sha == 'sha1':
                digest = SHA1.new(data)
                hash_lib = hashlib.sha1

            if self.key_type == self.SIGNATURE_RSA:
                signer = self.get_signer()
                if signer[0].verify(digest, sig):
                    result = 1
                elif signer[1].verify(digest, sig):
                    result = 2
            elif self.key_type == self.SIGNATURE_ECDSA:
                signer = self.get_signer()
                if signer.verify(sig, data, hash_lib, sigdecode=sigdecode_der):
                    result = 3
        except Exception as e:
            result = 0

        result_txt = self.SIGN_TYPE.get(result)

        if result > 0:
            result_txt += ' key size: ' + str(self.key_size) + ' bytes\nDigest: ' + digest.hexdigest()

        return result_txt


if __name__ == '__main__':
    pass
