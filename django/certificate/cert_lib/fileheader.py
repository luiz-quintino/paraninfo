from .__init__ import *
import time_uuid
from . import cert_parser as cp, blueprint as bp

raise_error = False  # Set to False to ignore errors and True to raise errors

H_HEADER_SIZE = 'HeaderSize'
H_FILE_SIZE = 'FileSize'
H_FILE_DIGEST = 'FileDigest'
H_SIGNING_NAME = 'SigningName'
H_SIGNING_KEY_IDENTIFIER = 'SigningKeyIdentifier'
H_TARGET_NAME = 'TargetName'
H_ROLLBACK_ID = 'RollbackId'
H_COMPATIBILITY_ID = 'CompatibilityId'
H_UUID = 'Uuid'
H_HEADER_SIGNATURE = 'HeaderSignature'
H_RESERVED = 'Reserved'

NODE_ROW_REGION = ('fc9a85041315')
NODE_CHINA_REGION = '140881c6fec8'

PADDING_0 = 0
PADDING_F = 1

CONVERSION_AUTO = -1
CONVERSION_BYTE = 0
CONVERSION_ORDERED = 1
CONVERSION_CHAR = 2
CONVERSION_BIN = 3
CONVERSION_UUID = 4

TYPE_HEX = 0
TYPE_INT = 1
TYPE_CHAR = 2
TYPE_BIN = 3

BIG_ENDIAN = 'big'
LITTLE_ENDIAN = 'little'


def is_valid_number(txt_hex='', bin_data=b'') -> bool:
    if not txt_hex and not bin_data:
        return False
    if txt_hex:
        try:
            my_int = int(txt_hex, 16)
        except:
            return False
    return True


def _finding_cert_in_data(data: bytes, begin=0) -> int:
    cert_list = [b'0\x82\x01', b'0\x82\x02', b'0\x82\x03', b'0\x82\x04', b'0\x82\x05']
    min_pos = len(data)
    for cert in cert_list:
        position = data.find(cert, begin)
        if position > -1:
            min_pos = position if position < min_pos else min_pos
    if min_pos < len(data):
        return min_pos + 1
    return 0


def define_data_type(bin_data: bytes) -> list:
    """
    Make a research inside the bin_data to determine the data type
        * certStore
        * DCL
        * Combined = certStore + DCL
    """
    data_type = 0  # auto
    shift_data = 0
    dcl_begin = 0
    index = 0

    cert_pos = _finding_cert_in_data(bin_data)
    if cert_pos == 1:    # found certificate in the begging
        data_type = 1

    elif b'\xff' * 0x240 == bin_data[:0x240] and \
            (b'\x00\x00\x00\xb0' == bin_data[0xe40 - 0x1c0: 0xe40 - 0x1c0 + 4] or
             b'\xb0\x00\x00\x00' == bin_data[0xe40 - 0x1c0: 0xe40 - 0x1c0 + 4]):
        data_type = 4  # found cal file

    elif cert_pos > 1:
        data_type = 1  # found certstore from a shift position
        shift_data = cert_pos - 1
        bin_data = bin_data[shift_data:]    # cut the after the shifter

    if data_type == 1:  # looking for a dcl after a certStore
        # cert_length = _finding_cert_in_data(bin_data, 3)    # next certificate
        # if cert_length == 0:
        cert_length = 1536  # standard certificate size (only one found)
        index = cert_length
        # else:
        #     index = cert_length - 1     # next certificate found
        while index < len(bin_data):    # looking for the end of the certificates
            if bin_data[index: index + 1] != b'\xff' and not _finding_cert_in_data(bin_data[index: index+3]):   # end of cert limiter
                if (len(bin_data) - index) > 95:
                    # looking for the sn padding
                    if _is_dcl(bin_data[index: index + 96]):
                        # identified dcl
                        data_type = 3  # combined
                        dcl_begin = index + shift_data
                        break
            index += cert_length

    if data_type == 0:  # auto and certStore not found
        if len(bin_data) % 96 == 0:
            for index in range(len(bin_data)-96+1):
                if _is_dcl(bin_data[index: index+96]):
                    data_type = 2  # dcl

    return [bin_data, shift_data, data_type, dcl_begin]


def _is_dcl(bin_data: bytes) -> bool:
    if bin_data[64: 64 + 4] == b'\xff' * 4 \
            or bin_data[64 + 32 - 4: 64 + 32] == b'\xff' * 4 \
            or bin_data[64: 64 + 4] == b'\x00' * 4 \
            or bin_data[64 + 32 - 4: 64 + 32] == b'\x00' * 4 \
            and 31 < ord(bin_data[: 1]) < 126 \
            and 31 < ord(bin_data[1: 2]) < 126 \
            and 31 < ord(bin_data[2: 3]) < 126 \
            and 31 < ord(bin_data[3: 4]) < 126:
        return True
    return False


class DCL:
    def __init__(self, bin_data=b'', csv_data='', shift=0):
        self.dcl_entry_size = 96
        self.dcl_name = ['issuerName',
                         'CertSerialNumber']
        self.dcl_field_size = [64, 32]
        self.dcl_conversion = [CONVERSION_CHAR, CONVERSION_BYTE]
        self.dcl = []
        self.shift = shift
        self.little_endian = False
        self.padding_left = False

        if bin_data:
            self.parse_dcl_bin(bin_data)
        elif csv_data:
            self.parse_dcl_csv(csv_data)

    def add_dcl_item(self, serial_number, common_name):
        if common_name and is_valid_number(txt_hex=serial_number):
            endian = 'little' if self.little_endian else 'big'
            if self.padding_left:
                dcl_byte = (b'\x00' * (32 - 20)) + int(serial_number, 16).to_bytes(20, endian)
            else:
                dcl_byte = int(serial_number, 16).to_bytes(20, endian) + (b'\x00' * (32 - 20))

            self.dcl.append([self._padding_string_dcl(common_name, 0), dcl_byte])

    def _padding_string_dcl(self, value: str, index: int) -> bytes:
        # Adjust a received string to the shift and order defined
        char = [ord(char) for char in value]
        if self.dcl_field_size[index] - len(value) > 0:
            char += (self.dcl_field_size[index] - len(value)) * [0]
        return bytes(char[:self.dcl_field_size[index]])

    def find_cert_in_dcl(self, issuer: str, serial: int) -> bool:
        dcl_name = self._padding_string_dcl(issuer, 0)
        padding_left = [True, True, False, False]
        little_endian = [False, True, False, True]
        data = [serial, serial, serial, serial]
        # Returns all possible values
        options = list(map(self.get_dcl_number, data, little_endian, padding_left))

        #
        # dcl_byte_pad1 = (self.dcl_field_size[1] * '00' + serial)[-self.dcl_field_size[1]*2:]
        # dcl_byte_pad2 = (serial + self.dcl_field_size[1] * '00')[:self.dcl_field_size[1]*2]
        # dcl_byte = [bytes.fromhex(dcl_byte_pad1), bytes.fromhex(dcl_byte_pad2)]

        for dcl_entry in self.dcl:
            if dcl_name in dcl_entry[0] and dcl_entry[1] in options:
                return True
        return False


    def get_dcl_number(self, data: int, little_endian=False, padding_left=False) -> bytes:
        endian = 'little' if little_endian else 'big'
        if padding_left:
            return (b'\x00' * (32 - 20)) + data.to_bytes(20, endian)
        else:
            return data.to_bytes(20, endian) + (b'\x00' * (32 - 20))

    def parse_dcl_csv(self, txt_data: str) -> bool:
        self.dcl = []
        result = False
        txt_data = txt_data.replace(',', ';')
        if txt_data:
            for dcl_issuer in txt_data.splitlines():
                if ';' in dcl_issuer:
                    dcl = dcl_issuer.split(';')
                    dcl_name = dcl[0].strip()
                    dcl_serial = dcl[1].strip()
                    self.add_dcl_item(dcl_serial, dcl_name)
                    result = True
        return result

    def parse_dcl_bin(self, dcl_data: bin) -> bool:
        if len(dcl_data) % 96 > 0:
            # return False
            pass
        self.dcl = []
        pointer = self.shift
        while pointer <= len(dcl_data):
            dcl_issuer = dcl_data[pointer: pointer + self.dcl_entry_size]
            if dcl_issuer:
                if dcl_issuer[0] != 255 and dcl_issuer[0] != 0:
                    text = dcl_issuer[:self.dcl_field_size[0]].decode(encoding='ISO-8859-1', errors='strict')
                    # for char in text:
                    #     # if the text is not printable, then finish the dcl table
                    #     if 32 > ord(char) > 0:
                    #         return True

                    self.dcl.append([dcl_issuer[:self.dcl_field_size[0]], dcl_issuer[-self.dcl_field_size[1]:]])
                else:
                    # if a invalid name (not character) is found, then finish the dcl table
                    break
            else:
                break
            pointer += self.dcl_entry_size

        return True

    def get_dcl_list(self) -> list:
        dcl_list = []
        for dcl_entry in self.dcl:
            # CONVERSION_CHAR
            name = dcl_entry[0].decode(encoding='ISO-8859-1', errors='strict')
            # CONVERSION_BYTE
            serial = dcl_entry[1].hex()
            dcl_list.append([name, serial])

        return dcl_list

    def get_dcl_bin(self) -> bytes:
        list = bytes()
        for dcl_entry in self.dcl:
            list += dcl_entry[0] + dcl_entry[1]
        return list

    def get_dcl_text(self) -> str:
        text = ''
        line = 0
        for dcl_entry in self.dcl:
            # CONVERSION_CHAR
            name = dcl_entry[0].decode(encoding='ISO-8859-1', errors='strict')
            # CONVERSION_BYTE
            serial = dcl_entry[1].hex()
            text += '{} {}: {}\n'.format(line, name, serial)
            line += 1
        if not text:
            text = 'The DCL list is empty'
        else:
            text += 'DCL size: {}'.format(len(self.dcl))
        return text

    def get_dcl_csv(self) -> str:
        text = 'IssuerName,SerialNumber\n'
        for dcl_entry in self.dcl:
            name = dcl_entry[0].decode(encoding='ISO-8859-1', errors='strict').strip(chr(0))
            serial = dcl_entry[1].hex()
            serial = serial[25:] if serial[0:24].rstrip('0') == '' else serial[:40]
            text += '{}; {}\n'.format(name.strip(), serial.strip('00'))
        return text


class CertStore(DCL):
    def __init__(self, cert_der=b'', cert_pem='', shift=0, csv_data=''):
        DCL.__init__(self, csv_data=csv_data)
        self.cert_entry_size = 1536
        self.cert_list = []
        self.cert_tree = {}
        self.shift = shift
        self.valid_certstore_sig = False


        if cert_der:
            self.parse_certstore_der(cert_der)
        elif cert_pem:
            self.parse_certstore_pem(cert_pem)

    def parse_certstore_der(self, cert_der: bin) -> bool:
        self.cert_list = []
        pointer = self.shift
        while pointer < len(cert_der):
            cert = cert_der[pointer: pointer + self.cert_entry_size]
            if _finding_cert_in_data(cert[:3]):    # Verify if it's a DER certificate
                cert_ob = cp.CertificateParser(cert_data=cert.rstrip(b'\xff'))
                if cert_ob.parsed:
                    self.cert_list.append(cert_ob)
            else:
                break
            pointer += self.cert_entry_size
        self._index_cert_tree()
        return True

    def parse_certstore_pem(self, cert_pem: str) -> bool:
        self.cert_list = []
        cert_list = self._get_der_cert(cert_pem)
        if cert_list:
            for item in cert_list:
                cert_ob = cp.CertificateParser(cert_data=item.encode())
                if cert_ob.parsed:
                    self.cert_list.append(cert_ob)
            self._index_cert_tree()
        return True

    def remove_cert(self, serial) -> bool:
        cert_sn_list = [cert.sn for cert in self.cert_list]
        if serial in cert_sn_list:
            self.cert_list.pop(cert_sn_list.index(serial))
            self.valid_certstore_sig = False
            self._index_cert_tree()

    def remove_dcl_item(self, serial_hex) -> bool:
        dcl_sn_list = [dcl[1] for dcl in self.get_dcl_list()]
        if serial_hex in dcl_sn_list:
            self.dcl.pop(dcl_sn_list.index(serial_hex))
            self.valid_certstore_sig = False
            self._index_cert_tree()

    def add_cert(self, cert_ob) -> bool:
        if cert_ob.parsed:
            self.cert_list.append(cert_ob)
            self.valid_certstore_sig = False
            self._index_cert_tree()
            return True
        return False

    def add_cert_to_dcl(self, cert_sn, cert_tn):
        self.add_dcl_item(cert_sn, cert_tn)
        self.valid_certstore_sig = False
        self._index_cert_tree()

    def add_dcl_obj(self, dcl: DCL):
        if dcl.dcl:
            self.dcl = dcl.dcl
            self.valid_certstore_sig = False
            self._index_cert_tree()

    def clear_cert_tree(self):
        self.cert_list = []
        self.valid_certstore_sig = False

    def _get_der_cert(self, data: str) -> list:
        border_list = ['-----BEGIN CERTIFICATE', 'END CERTIFICATE-----']
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

    def _index_cert_tree(self):
        self.cert_tree = {}
        for cert in self.cert_list:
            # self.cert_tree[cert.sn] = cert.get_cert_serialization(cert_type='DER')
            self.cert_tree[cert.sn] = cert

    def get_cert_tree(self) -> list:
        tree = []  # output tree
        list_tree = []  # list of certificates added to the tree view
        list_id = []  # list of certificate index added to the tree view
        list_cert_in_dcl = []   # list of certificate added to the dcl
        list_trust = []

        if self.dcl:  # if exist a dcl list, use it
            # look for the current certificate in the dcl
            id = 0  # index to create a sn + index to the duplicated sn
            for cert in self.cert_list:     # each certificate
                cn = cert.common_name
                tn = cert.target_name if cert.target_name else ''
                if self.find_cert_in_dcl(cn, cert.sn):
                    # if it is the 1st occurrence of this sn, include it in the black list
                    if cert.sn not in list_cert_in_dcl:
                        list_cert_in_dcl.append(cert.sn)    # black list
                        # list_tree.append(cert.sn)  # insert the list_tree entry
                        list_id.append(id)      # id list
                        tree.append(['in_dcl', hex(cert.sn)[2:], cn, cert.is_ca, tn, ''])
                id += 1

        for i in range(6):  # repeat 6 times to mount the tree independently of the input order
            id = 0  # index to create a sn + index to the duplicated sn
            for cert in self.cert_list:  # each certificate
                if cert.sn not in list_cert_in_dcl:
                    cn = cert.common_name
                    tn = cert.target_name if cert.target_name else ''
                    if cert.sn not in list_tree:  # new tree entry
                        # verify the signature
                        if cert.auth_sn:
                            cert_signer = self.cert_tree.get(cert.auth_sn)
                            if isinstance(cert_signer, cp.CertificateParser):
                                result = cert_signer.get_verify(sig=cert.sig, data=cert.tbs, cert_pem=cert_signer)
                                # result = bp.verify_sig_data(cert.tbs, cert.get_cert_decoded_pem(), cert.sig)
                            else:
                                result = ''
                        else:
                            # look for signer one by one
                            result = ''
                            for cert_signer in self.cert_list:
                                if cert_signer.get_verify(sig=cert.sig, data=cert.tbs, cert_pem=cert_signer):
                                    result = True
                                    cert.auth_sn = cert_signer.sn
                                    break

                        if result != '' and cert.auth_sn not in list_cert_in_dcl:  # signature valid
                            # verify if it's self signed
                            parent = 'root' if cert.sn == cert.auth_sn else hex(cert.auth_sn)[2:]
                            if parent == 'root' or cert.auth_sn in list_trust:  # parent already exist or it's a root
                                # create a new tree entry
                                tree.append([parent, hex(cert.sn)[2:], cn, cert.is_ca, tn, 'trusted'])
                                list_tree.append(cert.sn)  # insert the list_tree entry
                                list_id.append(id)  # insert the list with the index of the certificate
                                list_trust.append(cert.sn)
                            elif cert.auth_sn in list_tree:  # insert the list_tree for a non trusted
                                tree.append([parent, hex(cert.sn)[2:], cn, cert.is_ca, tn, ''])
                                list_tree.append(cert.sn)  # insert the list_tree entry
                                list_id.append(id)  # insert the list with the index of the certificate
                            # Certificate signature verification failed or not tracked to the root
                        else:
                            # signature fail or not tracked to the root
                            tree.append(['not_root', hex(cert.sn)[2:], cn, cert.is_ca, tn, ''])
                            list_tree.append(cert.sn)  # insert the list_tree entry
                            list_id.append(id)  # insert the list with the index of the certificate
                id += 1

        id = 0
        for cert in self.cert_list:
            if id not in list_id:   # ID's not in the list means the certificate is duplicated
                cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                tn = cert.target_name if cert.target_name else ''
                tree.append(['repeated', hex(cert.sn)[2:] + '#' + str(id), cn + '_index_' + str(id), cert.is_ca, tn, ''])
            id += 1

        if self.dcl:
            for dcl in self.get_dcl_list():
                tree.append(['dcl', dcl[1] + "*", dcl[0], '', '', ''])

        return tree

    def get_cert_tree_text(self) -> str:
        self.valid_certstore_sig = True
        output = 'cert_signer sn{:26} auth_sn{:33} ca{:1}  sign{}  id\n'.format('', '', '', '')
        for cert in self.cert_list:
            result = cert.validate_sign(self.cert_tree.get(cert.auth_sn), cert.sig, data=cert.tbs)
            output += '{:40} {:40} {}  {}\n'.format(hex(cert.sn)[2:],
                                                    hex(cert.auth_sn)[2:],
                                                    cert.is_ca,
                                                    result
                                                    )
            if not result:
                self.valid_certstore_sig = False
        output += 'CertStore size: {}  Valid: {}\n'.format(len(self.cert_list), self.valid_certstore_sig)
        return output

    def is_valid_certstore(self) -> bool:
        tree = self.get_cert_tree_text()
        return self.valid_certstore_sig

    def is_cert_in_certore(self, sn: int = 0, subject: str = '', auth_sn: str = ''):
        if sn > 0:
            for cert in self.cert_list:
                if sn == cert.sn:
                    return cert

        if auth_sn:
            for cert in self.cert_list:
                if cert.key_id in auth_sn:
                    return cert

        if subject:
            for cert in self.cert_list:
                if subject == cert.subject:
                    return cert

        return None

    def get_cert_list_der(self, selection=None) -> bin:
        value = self.get_cert_tree()
        sn_list = [item[1] for item in value if item[5] == 'trusted']
        out_list = b''
        for cert in self.cert_list:
            if hex(cert.sn)[2:] in sn_list:
                cert_der = cert.get_cert_serialization(cert_type='DER')
                cert_der = cert_der + (self.cert_entry_size - len(cert_der)) * b'\xff'
                out_list += cert_der

        return out_list

    def get_cert_list_pem(self, trusted=True) -> str:
        value = self.get_cert_tree()
        if trusted:
            sn_list = [item[1] for item in value if item[5] == 'trusted']
        else:
            sn_list = [item[1] for item in value]
        out_list = ''
        for cert in self.cert_list:
            if hex(cert.sn)[2:] in sn_list:
                cert_pem = cert.get_cert_serialization(cert_type='PEM').decode(encoding='ISO-8859-1', errors='strict')
                out_list += cert_pem

        return out_list


class FileHeader:
    def __init__(self, data=b'', little_endian=False):
        # order to convert bin_data
        self.little_endian = little_endian

        self.data_digest = None

        # SD15 header names
        self.header_names = [H_HEADER_SIZE,
                             H_FILE_SIZE,
                             H_FILE_DIGEST,
                             H_SIGNING_NAME,
                             H_SIGNING_KEY_IDENTIFIER,
                             H_TARGET_NAME,
                             H_ROLLBACK_ID,
                             H_COMPATIBILITY_ID,
                             H_UUID,
                             H_HEADER_SIGNATURE,
                             H_RESERVED]

        # flag to store the digest verification
        self.valid_file_digest = False

        # flag to store if the file header is valid (basically if it's 176B size)
        self.valid_header = False

        self.valid_file_size = None

        # flag to store if the file header signature is valid
        self.valid_sign = None

        self.errors_found = {H_HEADER_SIZE: 0,
                             H_FILE_SIZE: 0,
                             H_FILE_DIGEST: 0,
                             }

        # file with the certificate used to sign the header (pem, der or certStore)
        self.cert_signer_obj = None

        self.data = None    # file data

        # size of the file header fields
        self.dcl_field_size = [4, 4, 32, 64, 32, 16, 4, 4, 16, 256, 16]

        # converion type for the file header fields: 0 byte, 1 ordered(little or big), 2 char, 3 bin, 4 uuid
        self.conversion = [1, 1, 0, 2, 0, 2, 1, 1, 4, 0, 0]

        # padding type: 0 = '0', 1 = 'f'
        self.shift = [0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1]

        # file header fields (initially fulfilled with default padding values)
        self.header = {name: bytes(size * ([255] if pad else [0])) for name, size, pad in zip(self.header_names,
                                                                                              self.dcl_field_size,
                                                                                              self.shift)}
        if data:
            self.parse_header(data=data)
        else:  # Create a new empty header
            self.set_value(176, H_HEADER_SIZE, TYPE_INT)
            self.valid_header = True
            self.valid_file_size = True
            self.valid_file_digest = False

    def _padding_string(self, value, index):
        # Adjust a received string to the shift and order defined
        char = [ord(char) for char in value]
        if self.dcl_field_size[index] - len(value) > 0:
            char += (self.dcl_field_size[index] - len(value)) * ([255] if self.shift[index] else [0])
        return bytes(char[:self.dcl_field_size[index]])

    def set_value(self, value, name=H_SIGNING_NAME, value_type=TYPE_CHAR) -> bool:
        # set a value for a specified field of the header
        if name in self.header_names:
            index = self.header_names.index(name)
            if value_type == TYPE_CHAR and type(value) == str:
                self.header[name] = self._padding_string(value, index)
                self.valid_sign = False
                return True

            elif value_type == TYPE_BIN and type(value) == bytes:
                self.header[name] = (value +
                                     (self.dcl_field_size[index] *
                                      b'\xff' if self.shift[index] else b'x\00'))[:self.dcl_field_size[index]]
                self.valid_sign = False
                return True

            elif value_type == TYPE_HEX and type(value) == str:
                self.header[name] = bytes.fromhex(value +
                                                      (self.dcl_field_size[index] *
                                                       'ff' if self.shift[index] else '00'))[
                                    :self.dcl_field_size[index]]
                self.valid_sign = False
                return True

            elif value_type == TYPE_INT and type(value) == int:
                self.header[name] = int(value).to_bytes(length=self.dcl_field_size[index],
                                                        byteorder=(LITTLE_ENDIAN if self.little_endian else BIG_ENDIAN))
                self.valid_sign = False
                return True
        return False

    def set_file_data(self, file_data: bin) -> bool:
        # set the file bin_data and get the file bin_data information to complete the header
        self.data = file_data
        self.data_digest = self.get_data_hash(file_data)
        self.set_value(self.data_digest, H_FILE_DIGEST, TYPE_BIN)
        self.set_value(len(file_data), H_FILE_SIZE, TYPE_INT)
        self.valid_file_size = self.valid_file_digest = True
        self.valid_header = True
        self.valid_sign = False
        return True

    def is_valid_signature(self, cert_obj) -> str:
        # validate the signature from a given certificate
        try:
            pem = cert_obj.cert_data.public_key().\
                public_bytes(encoding=serialization.Encoding.PEM,
                             format=serialization.PublicFormat.SubjectPublicKeyInfo)
        except:
            return ''

        if cert_obj.key_type == cert_obj.SIGNATURE_RSA:
            pem = RSA.importKey(pem)

        data = self.get_header_bin()[:176]
        sig = self.get_value(H_HEADER_SIGNATURE, CONVERSION_BIN).rstrip(b'\xff')

        result = bp.verify_sig_data(data, pem, sig)
        if result:
            self.valid_sign = True
            self.cert_signer_obj = cert_obj
            return result

        self.valid_sign = False
        self.cert_signer_obj = None
        return ''

    def get_header_hash(self):
        # return an object hash hash form the header
        return SHA256.new(self.get_header_bin()[:176])

    def get_data_hash(self, data) -> bytes:
        # return a hex hash from a given bin_data
        return SHA256.new(data).digest()

    def get_header_dict(self) -> dict:
        # return a dictionary with the header fields
        return self.header

    def get_header_txt(self):
        # return a human readable information with the header fields and status
        text = ''
        if self.valid_header:
            for i in range(len(self.header_names)):
                word = self.get_value(self.header_names[i], self.conversion[i])
                text += '{}: {}\n'.format(self.header_names[i], word)
            text += 'FileDigest tested result: {}\nValid File Header: {}\nValide file size: {}\nValid header signature: {}' \
                .format(self.valid_file_digest, self.valid_header, self.valid_file_size, self.valid_sign)
        else:
            text = 'Not valid header'
        return text

    def get_value(self, name=H_TARGET_NAME, conversion=CONVERSION_AUTO):
        # return the value with the selected conversion
        word = ''
        if name in self.header_names:
            if conversion == CONVERSION_AUTO:
                conversion = self.conversion[self.header_names.index(name)]
            if conversion == CONVERSION_BYTE:
                word = self.header[name].hex()
            elif conversion == CONVERSION_ORDERED:
                word = str(int.from_bytes(self.header[name],
                                          byteorder=(LITTLE_ENDIAN if self.little_endian else BIG_ENDIAN)))
            elif conversion == CONVERSION_CHAR:
                word = self.header[name]
                word = word.decode(encoding='ISO-8859-1', errors='strict')
            elif conversion == CONVERSION_BIN:
                word = self.header[name]
            elif conversion == CONVERSION_UUID:
                word = self.get_uuid_parsed()

        return word

    def get_header_hex(self) -> str:
        # return the header in hex
        return self.get_header_bin().hex()

    def get_header_bin(self) -> bytes:
        # return the header in bin
        bin = bytes([])
        for v in self.header.values():
            bin += v
        return bin

    def get_uuid_parsed(self) -> str:
        # return the time stamp and node from header uuid
        node = self.header[H_UUID].hex()[-12:]
        try:
            ts = time_uuid.TimeUUID(bytes=self.header[H_UUID])
            if node == NODE_ROW_REGION:
                result = 'region is RoW'
            elif node == NODE_CHINA_REGION:
                result = 'region is China'
            else:
                result = 'region is RoW 0x' + node
            uuid_out = 'UUID Node: {}, Time stamp: {}'.format(result, ts.get_datetime())
            return uuid_out
        except Exception as e:
            return self.header[H_UUID].hex()

    def parse_header(self, data=b'') -> bool:
        # parse the header from a given bin file and validate some information

        if len(data) >= 448:
            header_bin = data[:448]
            data = data[448:]
        else:
            if raise_error:
                raise Exception('Header format error')
            self.valid_header = False
            return False

        point = 0
        for s, k in zip(self.dcl_field_size, self.header_names):
            bin_in = header_bin[point: point + s]
            self.header[k] = bin_in
            point += s

        # auto set endian
        self.valid_header = False
        if self.get_value(H_HEADER_SIZE) == '176':
            self.valid_header = True
        else:
            self.little_endian = True
            if self.get_value(H_HEADER_SIZE) == '176':
                self.valid_header = True
            else:
                self.errors_found[H_HEADER_SIZE] = self.get_value(H_HEADER_SIZE)

        self.data = data
        self.data_digest = self.get_data_hash(data)

        if self.data_digest == self.get_value(H_FILE_DIGEST, CONVERSION_BIN):
            self.valid_file_digest = True
        else:
            self.valid_file_digest = False
            self.errors_found[H_FILE_DIGEST] = self.data_digest.hex()

        if int(self.get_value(H_FILE_SIZE)) == len(data):
            self.valid_file_size = True
        else:
            self.valid_file_size = False
            self.errors_found[H_FILE_SIZE] = len(data)

        return True


if __name__ == '__main__':
    pass
