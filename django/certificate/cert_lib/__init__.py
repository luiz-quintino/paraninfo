import file_io as fio
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import utils
from Crypto.Signature import PKCS1_PSS
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import Crypto.PublicKey.RSA as RSA
import time_uuid
import random
from datetime import datetime, timedelta
import ipaddress