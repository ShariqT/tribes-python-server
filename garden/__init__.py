import base64
from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm, CompressionAlgorithm
import pgpy

def lwe_headers_exist(headers):
  if 'x-lwe-key' not in headers:
    return False
  return True

def urlsafe_base64_encode(data: bytes) -> str:
  """
  Encodes bytes-like data using URL-safe Base64 encoding, removing padding.
  
  Args:
      data: The bytes-like object to encode.
  
  Returns:
      A URL-safe Base64 encoded string.
  """
  encoded_bytes = base64.urlsafe_b64encode(data).rstrip(b'=')
  return encoded_bytes.decode('utf-8')

def urlsafe_base64_decode(encoded_data: str) -> bytes:
  encoded_data_bytes = encoded_data.encode('utf-8')
  padding_needed = len(encoded_data_bytes) % 4
  if padding_needed:
      encoded_data_bytes += b'=' * (4 - padding_needed)
  return base64.urlsafe_b64decode(encoded_data_bytes)


def get_username_uuid(username):
  return "123-abcde-456-abce"



def open_keyfile(keyfile_path):
  key, _ = pgpy.PGPKey.from_file(keyfile_path)
  return key

def create_key_from_text(keydata):
  key, _ = pgpy.PGPKey.from_blob(keydata)
  return key

def create_pgpmessage_from_text(message_text):
  return pgpy.PGPMessage.from_blob(message_text)

def create_key_pair(username, email):
  key = pgpy.PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 4096)
  uid = pgpy.PGPUID.new(username, email=email)
  key.add_uid(uid, usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
    hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512, HashAlgorithm.SHA224],
    ciphers=[SymmetricKeyAlgorithm.AES256, SymmetricKeyAlgorithm.AES192, SymmetricKeyAlgorithm.AES128],
    compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP, CompressionAlgorithm.Uncompressed])

  return key

def encrypt_message(message, public_key):
  message = pgpy.PGPMessage.new(message)
  encrypted_message = public_key.encrypt(message)
  return encrypted_message


def decrypt_message(encrypted_message, secret_key):
  try:
    return secret_key.decrypt(encrypted_message)
  except Exception as e:
    raise Exception("could not decrypt message")


def generate_key_name_id(public_key):
  key_users = public_key.userids
  name_id = key_users[0].name + "-" + public_key.fingerprint[-8:]
  return name_id