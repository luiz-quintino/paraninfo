from .__init__ import *
from typing import Tuple, List, Any
from os import urandom
from . import cert_parser as cp

P_COMMON_NAME = 'common_name'
P_COUNTRY = 'country'
P_LOCALITY = 'locality'
P_STATE = 'state'
P_ORGANIZATION = 'organization'
P_VALIDATION = 'validation'
P_CA = 'ca'
P_DIGITAL_SIGNATURE = 'digital_signature'
P_CONTENT_COMMITMENT = 'content_commitment'
P_KEY_ENCIPHERMENT = 'key_encipherment'
P_DATA_ENCIPHERMENT = 'data_encipherment'
P_KEY_CERT_SIGN = 'key_cert_sign'
P_KEY_AGREEMENT = 'key_agreement'
P_CRL_SIGN = 'crl_sign'
P_ENCIPHER_ONLY = 'encipher_only'
P_DECIPHER_ONLY = 'decipher_only'
P_BASIC_CONSTRAINTS = 'basic_constraints'
P_KEY_ID = 'key_id'
P_AUTH_KEY_IDENTIFIER = 'auth_key_identifier'
P_SUBJECT_KEY_IDENTIFIER = 'subject_key_identifier'
P_TARGET_NAME = 'target_name'
P_EXTENDED_KEY_USAGE = 'extended_key_usage'


K_OID_BOOTLOADER = '1.3.6.1.4.1.29858.3.1.2.1'
K_OID_FIRMWARE = '1.3.6.1.4.1.29858.3.1.2.3'
K_OID_CALIBRATION = '1.3.6.1.4.1.29858.3.1.2.4'
K_OID_CERTSTORE_AND_DCL = '1.3.6.1.4.1.29858.3.1.2.5'
K_OID_HTA_FIRMWARE = '1.3.6.1.4.1.29858.3.1.2.12'
K_OID_CO_PROC_FIRMWARE = '1.3.6.1.4.1.29858.3.1.2.13'
K_OID_CO_HOSTED_APP = '1.3.6.1.4.1.29858.3.1.2.14'
K_OID_CO_HOSTED_CONFIG = '1.3.6.1.4.1.29858.3.1.2.15'
K_OID_MAP = '1.3.6.1.4.1.29858.3.1.2.16'
K_OID_FORENSIC_FIRMWARE = '1.3.6.1.4.1.29858.3.1.2.17'
K_OID_SAM = '1.3.6.1.4.1.29858.3.1.2.18'
K_OID_INVENTORY = '1.3.6.1.4.1.29858.3.1.2.19'
K_OID_AUTHENTICATED_DIAGNOSTIC_ACCESS = '1.3.6.1.4.1.29858.3.1.1.1'
K_AUTHORIZED_ROLE = '1.3.6.1.4.1.29858.3.2.1.1'
K_OID_TARGET_NAME = '1.3.6.1.4.1.29858.3.2.1.2'
K_AUTH_ROLE_GROUP = '1.3.6.1.4.1.29858.3.2.1.3'
K_AUTH_ROLE_TEXT = '1.3.6.1.4.1.29858.3.2.1.4'
K_ECU_TARGET_DETAIL = '1.3.6.1.4.1.29858.3.2.1.5'


raise_error = True  # Set to False to ignore errors and True to raise errors


def get_nameoid() -> list:
    names = []
    for nameoid in NameOID.__dict__.values():
        if type(nameoid).__name__ == 'ObjectIdentifier':
            names.append(nameoid._name)
    return names


def create_sn(size: int) -> int:
    return int.from_bytes(urandom(size), "big") >> 1


KEY_TYPE = ['RSA', 'ECC']
KEY_SIZE = {'RSA': {'tile': 'RSA modulus size',
                    'values': [1024, 2048, 3072, 4096]},
            'ECC': {'tile': 'Curve',
                    'values': [256, 384, 521]}
            }
HASH_SIZE = ['SHA1', 'SHA256', 'SHA384', 'SHA512']
HASH_SIGN = {'': hashes.SHA256(),
             'SHA1': hashes.SHA1(),
             'SHA256': hashes.SHA256(),
             'SHA384': hashes.SHA384(),
             'SHA512': hashes.SHA512()
             }

DURATION_UNIT = {'day': 1, 'week': 7, 'month': 30, 'year': 365, 'decade': 3652.5}

KEY_USAGES = ['digital_signature', 'content_commitment', 'key_encipherment', 'data_encipherment',
              'key_cert_sign', 'key_agreement', 'crl_sign', 'encipher_only', 'decipher_only']

EXT_KEY_USAGES = ['codeSigning', 'emailProtection', 'ipsecEndSystem', 'ipsecTunnel', 'ipsecUser',
                  'timeStamping', 'OCSPSigning', 'serverAuth', 'clientAuth', 'custom']

SUB_ALT_NAME = ['otherName', 'email', 'DNS', 'URI', 'IP', '']
# SUB_ALT_NAME = ['otherName', 'email', 'DNS', 'URI', 'IP']


class CertificateBuilder:
    def __init__(self):
        self.subject = {
            'commonName': 'my certificate'
        }
        self.identification = {
            'serial number size': 20,
            'serial number': '',
            'key id': '',
            'authorityInfoAccess': [],
            'cRLDistributionPoints': [],
            'certificatePolicies': [],
        }
        self.keys_algorithm = {
            'algorithm type': 'RSA',
            'key size': 2048,
            'sign hash size': 'SHA256',
            'secret key': '',
            'public key': '',
            'keys': 'None',

        }
        self.validity = {
            'duration': 1,
            'unit': 'year'
        }
        self.basic_constraints = {
            'basic constraints': True,
            'include basic constraints': True,
            'path': 0,
            'key usage': [],
            'extended key': [],
        }
        self.key_identifier = {
            'include key id': True,
            'include authority key id': True,
            'include authority issuer': False,
        }

        self.alternative_name = []
        self.arbitrary_extensions = []
        self.key_password = ''
        self.load_key_password = ''

        self.issuer = {
            'certificate path': '',
            'certificate cn': '',
            'secret key path': ''
        }

        self.last_change_section = ''

        self.key_usages = {
            P_DIGITAL_SIGNATURE: False,
            P_CONTENT_COMMITMENT: False,
            P_KEY_ENCIPHERMENT: False,
            P_DATA_ENCIPHERMENT: False,
            P_KEY_CERT_SIGN: True,
            P_KEY_AGREEMENT: False,
            P_CRL_SIGN: True,
            P_ENCIPHER_ONLY: False,
            P_DECIPHER_ONLY: False,
        }

        self.pem = None
        self.der = None
        self.private_key = None
        self.public_key = None
        self.public_key_obj = None
        self.csr = None

        self.from_csr = False

        """
        Default parameters. 
        Should be replaced in order to configure the certificate before call the generate_cert()
        """

    def load_secret_key(self, file_name: str, psw: str):
        try:
            if psw:
                if type(psw) == str:
                    psw = psw.encode()
            else:
                psw = None

            key_data = fio.open_file(file_name)
            return serialization.load_pem_private_key(key_data,
                                                      password=psw,
                                                      backend=default_backend()), ''
        except Exception as e:
            return None, e

    def build_certificate(self):
        # Verify needed inputs for signature
        if self.issuer.get('certificate path') and not self.issuer.get('secret key path') \
                or not self.issuer.get('certificate path') and self.issuer.get('secret key path'):
            return 'Missing certificate or private key'

        # Load private key for not self signing certificate
        if self.issuer.get('secret key path'):
            key_signer, error = self.load_secret_key(self.issuer.get('secret key path'), self.load_key_password)
            if error:
                return 'Chave de certificado errada\n' + str(error)

        # Generate the DN
        name = self._generate_name()

        # Signer certificate info
        if self.issuer.get('certificate path'):  #
            # Take the information from the cert signer
            cp.raise_error = True
            cert_signer = cp.CertificateParser(fio.open_file(self.issuer.get('certificate path')))
            issuer_name = cert_signer.subject
            auth_serial_number = cert_signer.sn
            auth_key_id = bytes.fromhex(cert_signer.key_id) if \
                cert_signer.auth_key_id else None
        else:  # Self signed
            key_signer = self.keys_algorithm['keys'].key_pair
            issuer_name = name
            auth_serial_number = self.identification.get('serial number')
            auth_key_id = SHA256.new(self.keys_algorithm['keys'].public_key.encode()).digest()

        # Generate validity
        now = datetime.utcnow()
        validation = int(DURATION_UNIT.get(self.validity.get('unit')) * self.validity.get('duration'))

        # Build the certificate
        cert = (
            x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(issuer_name)
                .public_key(self.public_key_obj)
                .serial_number(self.identification.get('serial number'))
                .not_valid_before(now)
                .not_valid_after(now + timedelta(days=validation))
        )

        # Add subject key identifier
        if self.key_identifier.get('include key id'):
            subject_key_identifier = x509.SubjectKeyIdentifier(
                digest=SHA256.new(self.keys_algorithm['keys'].public_key.encode()).digest())
            cert = cert.add_extension(subject_key_identifier, False)

        # Add basic constraints (CA)
        if self.basic_constraints.get('include basic constraints') or self.basic_constraints.get('basic constraints'):
            basic_constraints = x509.BasicConstraints(ca=self.basic_constraints.get('basic constraints'),
                                                      path_length=None)
            cert = cert.add_extension(basic_constraints, self.basic_constraints.get('basic constraints'))

        # Add key usage
        self._generate_key_usages()   # Generate the key usage
        key_usage = x509.KeyUsage(digital_signature=self.key_usages[P_DIGITAL_SIGNATURE],
                                  content_commitment=self.key_usages[P_CONTENT_COMMITMENT],
                                  key_encipherment=self.key_usages[P_KEY_ENCIPHERMENT],
                                  data_encipherment=self.key_usages[P_DATA_ENCIPHERMENT],
                                  key_agreement=self.key_usages[P_KEY_AGREEMENT],
                                  key_cert_sign=self.key_usages[P_KEY_CERT_SIGN],
                                  crl_sign=self.key_usages[P_CRL_SIGN],
                                  encipher_only=self.key_usages[P_ENCIPHER_ONLY],
                                  decipher_only=self.key_usages[P_DECIPHER_ONLY])
        cert = cert.add_extension(key_usage, True)

        # Add key usage: extended key usage
        if not self.basic_constraints.get('basic constraints'):
            if self.basic_constraints['extended key']:
                key_usages = []
                critical = False
                for item in self.basic_constraints['extended key']:
                    oid_key_usage = '2.5.29.37.0'   # Any
                    critical = True if item.endswith('*') else False
                    item = item.rstrip('*')
                    if item.startswith('custom'):   # item = ['custom:1.2.3.4*']
                        oid_key_usage = item.split(':')[-1]
                        if oid_key_usage not in cp.KEY_USAGE.keys():
                            if oid_key_usage in cp.KEY_USAGE.values():
                                oid_key_usage = list(cp.KEY_USAGE.keys())[list(cp.KEY_USAGE.values()).index(oid_key_usage)]
                        key_usages.append(x509.ObjectIdentifier(oid_key_usage))
                    else:                           # item = [codeSigning*]
                        extended_list = list(x509.oid.ExtendedKeyUsageOID.__dict__.items())
                        critical = True
                        for extend_key in extended_list:
                            if not extend_key[0].startswith('_'):
                                if extend_key[1]._name == item:
                                    oid_key_usage = extend_key[1].dotted_string
                                    key_usages.append(x509.ObjectIdentifier(oid_key_usage))
                                    break

                extended_key_usage = x509.ExtendedKeyUsage(key_usages)
                cert = cert.add_extension(extended_key_usage, critical)

        # Add extensions: subject alt name
        if self.alternative_name:
            alternative_name, error = self._generate_alternative_names()
            if error:
                return error

            cert = cert.add_extension(x509.SubjectAlternativeName(alternative_name), False)

        # Add information: authorityInfoAccess
        if self.identification.get('authorityInfoAccess'):
            acss_description = []
            for info in self.identification['authorityInfoAccess']:
                critical = True if ''.endswith('*') else False
                info = info.strip('*').split(',')
                acss_method = x509.ObjectIdentifier(info[0].strip())
                acss_location = x509.UniformResourceIdentifier(info[1].strip())
                acss_description.append(x509.AccessDescription(acss_method, acss_location))
            cert = cert.add_extension(x509.AuthorityInformationAccess(acss_description), critical)

        # Add information: cRLDistributionPoints
        if self.identification.get('cRLDistributionPoints'):
            dist_points = []
            for info in self.identification['cRLDistributionPoints']:
                critical = True if ''.endswith('*') else False
                info = info.strip('*')
                acss_location = x509.UniformResourceIdentifier(info.strip())
                dist_points.append(x509.DistributionPoint([acss_location], None, None, None))
            cert = cert.add_extension(x509.CRLDistributionPoints(dist_points), critical)

        # Add information: certificatePolicies
        if self.identification.get('certificatePolicies'):
            cert_policies = []
            for info in self.identification['certificatePolicies']:
                critical = True if ''.endswith('*') else False
                info = info.strip('*').split(',')
                acss_method = x509.ObjectIdentifier(info[0].strip())
                plcy_qualifier = [info[1].strip()]
                # plcy_qualifier = [x509.UserNotice(None, info[1].strip())]
                cert_policies.append(x509.PolicyInformation(acss_method, plcy_qualifier))
            cert = cert.add_extension(x509.CertificatePolicies(cert_policies), critical)

        # Add extensions: arbitrary extensions
        for item in self.arbitrary_extensions:
            item_obj = item.split(':')      # item = [name:oid:value*]
            critical = True if item_obj[2].endswith('*') else False
            extension = x509.UnrecognizedExtension(x509.ObjectIdentifier(item_obj[1]),
                                                   b'\x13\x04' + item_obj[2].rstrip('*').encode())
            cert = cert.add_extension(extension, critical)

        # Add extension: authority key identifier
        if (self.key_identifier.get('include authority key id')
                or self.key_identifier.get('include authority issuer')):
            issuer = [x509.DirectoryName(issuer_name)]
            auth_key_identifier = self._generate_auth_key_id(auth_key_id, issuer, auth_serial_number)
            cert = cert.add_extension(auth_key_identifier, False)

        # Sing the certificate
        try:
            cert = cert.sign(key_signer, HASH_SIGN.get(self.keys_algorithm.get('sign hash size')), default_backend())
        except Exception as e:
            return e

        # Encode the certificate
        self.pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
        self.der = cert.public_bytes(encoding=serialization.Encoding.DER)
        return 'success'

    def build_csr(self):
        name = self._generate_name()
        key = self.keys_algorithm['keys'].key_pair
        alternative_names, error = self._generate_alternative_names()
        if error:
            return error

        csr = (x509.CertificateSigningRequestBuilder()
               .subject_name(name)
               )
        if alternative_names:
            csr = csr.add_extension(x509.SubjectAlternativeName(alternative_names), critical=False)
        csr = csr.sign(key, HASH_SIGN.get(self.keys_algorithm.get('sign hash size')))
        self.csr = csr.public_bytes(encoding=serialization.Encoding.PEM)

    def _generate_alternative_names(self) -> Tuple[List[Any], str]:
        alternative_name = []
        for name in self.alternative_name:
            if name.startswith('DNS'):
                item = name.split(':')  # name = ['DNS:url']
                alternative_name.append(x509.DNSName(item[1].rstrip('*')))
            if name.startswith('IP'):
                item = name.split(':')  # name = ['IP:address']
                alternative_name.append(x509.IPAddress(ipaddress.ip_address(item[1].rstrip('*'))))
            if name.startswith('otherName'):
                item = name.split(':')[1].rstrip('*').split(',')     # name = ['OID:value']
                if len(item) < 2:
                    return [], 'error: OtherName format is "OID, value"'
                oid = x509.ObjectIdentifier(item[0].rstrip())
                value = item[1].rstrip().encode()
                value = b'\x13' + chr(len(value)).encode() + value
                alternative_name.append(x509.OtherName(oid, value))
            if name.startswith('URI'):
                item = name.split(':')  # name = ['URI:url']
                alternative_name.append(x509.UniformResourceIdentifier(item[1].rstrip('*')))
            if name.startswith('email'):
                item = name.split(':')  # name = ['email:address']
                alternative_name.append(x509.RFC822Name(item[1].rstrip('*')))
        return alternative_name, ''

    def _generate_auth_key_id(self, auth_key_id, issuer, auth_serial_number):
        if self.key_identifier.get('include authority key id') and self.key_identifier.get('include authority issuer'):
            return x509.AuthorityKeyIdentifier(
                key_identifier=auth_key_id,
                authority_cert_issuer=issuer,
                authority_cert_serial_number=auth_serial_number)
        elif self.key_identifier.get('include authority issuer'):
            return x509.AuthorityKeyIdentifier(
                key_identifier=None,
                authority_cert_issuer=issuer,
                authority_cert_serial_number=auth_serial_number)
        elif self.key_identifier.get('include authority key id'):
            return x509.AuthorityKeyIdentifier(
                key_identifier=auth_key_id,
                authority_cert_issuer=None,
                authority_cert_serial_number=None)

    def _generate_name(self):
        name_list = []
        for name, value in self.subject.items():
            for nameoid in NameOID.__dict__.values():
                if type(nameoid).__name__ == 'ObjectIdentifier':
                    if nameoid._name == name.split()[0]:
                        name_list.append(x509.NameAttribute(nameoid, value))
                        break
        return x509.Name(name_list)

    def _generate_key_usages(self):
        for item, value in self.key_usages.items():
            if item in self.basic_constraints.get('key usage') or item + '*' in self.basic_constraints.get('key usage'):
                self.key_usages[item] = True
            else:
                self.key_usages[item] = False

    def load_csr(self, file_name):
        try:
            csr = x509.load_pem_x509_csr(fio.open_file(file_name), backend=default_backend())
        except Exception as e:
            return None
        return csr


class Keys:
    def __init__(self, key_type: str = '', key_size: str = '', file_name: str = '', psw=''):
        self.key_type = key_type
        self.key_size = int(key_size) if key_size else None
        self.file_name = file_name
        self.key_pair = None
        self.public_key = None
        self.error = None
        self.psw = psw

        if self.key_type == 'RSA' and key_size:
            self._key_rsa()
        elif self.key_type == 'ECC' and key_size:
            self._key_ecc()
        elif self.file_name:
            self._load_key()
        else:
            self.error = 'Missing parameters to create the key'

    def _load_key(self):
        data_key = fio.open_file(self.file_name)
        if self.psw:
            if type(self.psw) == str:
                self.psw = self.psw.encode()
        else:
            self.psw = None
        if data_key:
            try:
                self.key_pair = serialization.load_pem_private_key(data_key, password=self.psw, backend=default_backend())
            except Exception as e:
                self.error = 'Wrong file or password.\nError converting the private key or wrong password'
                return
        else:
            self.error = 'Wrong file.\nError loading the private key'
            return

        self.key_size = self.key_pair.key_size
        if self.key_size in [160, 256, 384, 521]:
            self.key_type = 'ECC'
            self.public_key = hex(self.key_pair.public_key().public_numbers().x)[3:]
        elif self.key_size in [1024, 2048, 3072, 4096]:
            self.public_key = hex(self.key_pair.public_key().public_numbers().n)[3:]
            self.key_type = 'RSA'

    def get_public_pem(self):
        return self.key_pair.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)

    def get_private_pem(self):
        if self.psw:
            if type(self.psw) == str:
                self.psw = self.psw.encode()

            return self.key_pair.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.BestAvailableEncryption(self.psw), )
        else:
            return self.key_pair.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(), )

    def _key_rsa(self):
        self.key_pair = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend(), )
        self.public_key = hex(self.key_pair.public_key().public_numbers().n)[3:]

    def _key_ecc(self):
        size = ec.SECP256K1()   # Default 256
        if self.key_size == 384:
            size = ec.SECP384R1()
        elif self.key_size == 521:
            size = ec.SECP521R1()

        self.key_pair = ec.generate_private_key(
            size, backend=default_backend(), )
        self.public_key = hex(self.key_pair.public_key().public_numbers().x)[3:]

    def get_public_key_serialization(self, key):
        return key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)


if __name__ == '__main__':
    pass

