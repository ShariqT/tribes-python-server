import redis
import uuid
import garden
import json
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from . import pool


message_schema = (
    TextField("$.message_id", as_name="message_id"),
    TextField("$.from_print", as_name="from_print"), # pgp fingerprint
    TextField("$.to_print", as_name="to_print"), # pgp fingerprint
    TextField("$.from_username", as_name="from"),
    TextField("$.to_username", as_name="to"),
    TextField("$.message", as_name="message"), # pgp message
    NumericField("$.is_read", as_name="read") # 0 or 1
)


def create_message_index():
  try:
    r = redis.Redis(connection_pool=pool)
    r.ft(f"idx:messages").create_index(
      message_schema,
      definition=IndexDefinition(
          prefix=["message:"], index_type=IndexType.JSON
      )
    )
    r.close()
  except:
    raise Exception(f"Could not create messages index")

def get_messages_for_superuser():
  r = redis.Redis(connection_pool=pool)
  admin_keytext = r.get("superuser")
  admin_key = garden.create_key_from_text(admin_keytext)
  admin_fingerprint = admin_key.fingerprint
  query_results = r.ft("idx:messages").search(Query(f"@to_print:{admin_fingerprint}"))
  r.close()
  all_messages = []
  for result in query_results['results']:
    all_messages.append(ServerMessage.load_by_dict(json.loads(result['extra_attributes']['$'])))
  return all_messages

def get_message_by_id(message_id):
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:messages").search(Query(f"@message_id:{message_id}"))
    if len(query_results['results']) == 0:
      raise Exception(f"There is no such message with id {message_id}")
    return ServerMessage.load_by_dict(json.loads(query_results['results'][0]['extra_attributes']['$']))
  except:
    raise Exception(f"Could not get info for message {message_id}")

def get_messages_by_key(requestor_key):
  try:
    requestors_messages = []
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:messages").search(Query(f"@to_print: { requestor_key.fingerprint }"))
    if  len(query_results['results']) == 0:
      return []
    for result in query_results['results']:
      requestors_messages.append(ServerMessage.load_by_dict(json.loads(result['extra_attributes']['$'])))
    return requestors_messages
  except Exception as e:
    raise Exception(f"Could not get messages for requested public key {str(e)}")

def get_all_messages():
  r = redis.Redis(connection_pool=pool)
  query_results = r.ft("idx:messages").search(Query("*"))
  r.close()
  all_messages = []
  for result in query_results['results']:
    all_messages.append(ServerMessage.load_by_dict(json.loads(result['extra_attributes']['$'])))
  return all_messages

# ServerMessages will be encrypted with the server public key. 
# The to and from publickey are there for a reference so that 
# people will known who sent them the message. The to_key and the
# from_key do not have any part in decrypting or encrypting
# for this class. 
class ServerMessage():
  def __init__(self, message):
    self.message = None
    self.message_plaintext = message
    self.from_fingerprint = None
    self.to_fingerprint = None
    self.from_username = None
    self.to_username = None
    self.id = None
    self.is_read = 0
  
  def __repr__(self):
    if self.id is not None:
      return f"ServerMessage loaded from id {self.id}"
    return f"ServerMessage: (Draft) from {self.from_username} to {self.to_username}"
  
  @classmethod
  def load_by_dict(cls, attribs):
    new_message = cls(None)
    new_message.id = attribs['message_id']
    new_message.message = garden.create_pgpmessage_from_text(attribs['message'])
    new_message.from_fingerprint = attribs['from_print']
    new_message.to_fingerprint = attribs['to_print']
    new_message.to_username = attribs['to_username']
    new_message.from_username = attribs['from_username']
    return new_message
  

  def decrypt_message(self, private_key):
    self.message_plaintext = garden.decrypt_message(self.message, private_key).message
    self.is_read = 1
    return True    
  
  def save_message(self):
    try:
      r = redis.Redis(connection_pool=pool)
      r.json().set(f"message:{self.id}", Path.root_path(), {
        "message_id": self.id,
        "from_print": self.from_fingerprint, 
        "to_print": self.to_fingerprint,
        "from_username": self.from_username,
        "to_username": self.to_username,
        "message": str(self.message),
        "is_read": self.is_read
      })
      r.close()
    except:
      raise Exception(f"Could not save message")
  
  def create_message(self, server_publickey):
    if (self.to_fingerprint is None or self.from_fingerprint is None):
      raise Exception("Cannot create new messages without a receipent public key and a sender public key")
    if self.to_username is None or self.from_username is None:
      raise Exception("Cannot create new messages without a receiptent and sender username")
    # self.to_fingerprint = self.tofingerprint
    # self.from_fingerprint = self.from_key.fingerprint
    # self.to_username = garden.generate_key_name_id(self.to_key)
    # self.from_username = garden.generate_key_name_id(self.from_key)
    self.message = garden.encrypt_message(self.message_plaintext, server_publickey)
    self.id = uuid.uuid4().hex
    self.save_message()
    
    




