import redis
import uuid
import garden
import json
import os
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from dotenv import load_dotenv
load_dotenv()

pool = redis.ConnectionPool(
  host=os.environ['REDIS_HOST'], 
  port=os.environ['REDIS_PORT'], 
  db=os.environ['REDIS_DB'], 
  protocol=3, 
  decode_responses=True)

member_schema = (
    TextField("$.key", as_name="key"),
    TextField("$.fingerprint", as_name="fingerprint"),
    TextField("$.username", as_name="username")
)





def create_people_index(people_type = "members"):
  type_prefix = "member:"
  if people_type == "moderators":
    type_prefix = "moderator:"
  if people_type == "blocked":
    type_prefix = "block:"
  try:
    r = redis.Redis(connection_pool=pool)
    r.ft(f"idx:{people_type}").create_index(
      member_schema,
      definition=IndexDefinition(
          prefix=[type_prefix], index_type=IndexType.JSON
      )
    )
    r.close()
  except Exception as e:
    raise Exception(f"Could not create {type_prefix} index because {e}")


def format_moderator_results(results):
  returned_results = []
  for unformatted_result in results['results']:
      attribs = json.loads(unformatted_result['extra_attributes']['$'])
      returned_results.append({
        'id': unformatted_result['id'],
        'key':attribs['key'],
        'username': attribs['username'],
        'fingerprint': attribs['fingerprint']
      })
  return returned_results

def add_moderator(moderator_public_key):
  username = garden.generate_key_name_id(moderator_public_key)
  query_results = search_moderator(moderator_public_key)
  if len(query_results) != 0:
    raise Exception("This public key is already a moderator")
  try:
    r = redis.Redis(connection_pool=pool)
    id = uuid.uuid4().hex
    r.json().set(f"moderator:{id}", Path.root_path(), {"key": str(moderator_public_key), "fingerprint": moderator_public_key.fingerprint, "username": username })
    r.close()
  except:
    raise Exception(f"Could not save public key for {username} in moderator key")

def delete_moderator(moderator_id):
  try:
    r = redis.Redis(connection_pool=pool)
    r.delete(moderator_id)
    r.close()
  except:
    raise Exception(f"could not delete id {moderator_id}")

def view_moderators():
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:moderators").search(Query("*"))
    results = format_moderator_results(query_results)
    r.close()
    return results
  except:
    raise Exception("Could not query moderatos key")

def find_moderator_by_username(username):
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:moderators").search(
      Query(f"@username: {username}")
    )
    r.close()
    results = format_moderator_results(query_results)
    return results
  except:
    raise Exception("Could not find moderator")


def search_moderator(moderator_public_key):
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:moderators").search(
      Query(moderator_public_key.fingerprint)
    )
    results = format_moderator_results(query_results)
    r.close()
    return results
  except:
    raise Exception("Could not find public from moderator key")


def get_admin_username():
  try:
    r = redis.Redis(connection_pool=pool)
    username = r.get("superuser_username")
    return username
  except:
    raise Exception("Could not get superuser's name")

def get_admin_publickey():
  try:
    r = redis.Redis(connection_pool=pool)
    publickey = r.get("superuser")
    return garden.create_key_from_text(publickey)
  except:
    raise Exception("Couldd not get ")


def add_member(member_public_key):
  username = garden.generate_key_name_id(member_public_key)
  query_results = search_member(member_public_key)
  if len(query_results) != 0:
    raise Exception("This public key is already a member")
  try:
    r = redis.Redis(connection_pool=pool)
    id = uuid.uuid4().hex
    r.json().set(f"member:{id}", Path.root_path(), {"key": str(member_public_key), "fingerprint": member_public_key.fingerprint, "username": username })
    r.close()
  except Exception as e:
    print(e)
    raise Exception(f"Could not save public key for {username} in member key")

def search_member(member_public_key):
  try:
    print(type(member_public_key))
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:members").search(
      Query(member_public_key.pubkey.fingerprint)
    )
    results = format_moderator_results(query_results)
    r.close()
    return results
  except Exception as e:
    print(e)
    raise Exception("Could not find public from member key")


def block_key(member_public_key):
  username = garden.generate_key_name_id(member_public_key)
  try:
    r = redis.Redis(connection_pool=pool)
    id = uuid.uuid4().hex
    r.json().set(f"block:{id}", Path.root_path(), {"key": str(member_public_key), "fingerprint": member_public_key.fingerprint, "username": username })
    r.close()
  except Exception as e:
    print(e)
    raise Exception(f"Could not save public key for {username} in block key")

def is_key_blocked(member_public_key):
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:blocked").search(Query(member_public_key.fingerprint))
    r.close()
    if len(query_results['results']) == 1:
      return True
    else:
      return False
  except Exception as e:
    print(f"is key blocked {e}")
    raise Exception(f"There was an error processing the block list: {e}")

def view_members():
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:members").search(Query("*"))
    results = format_moderator_results(query_results)
    r.close()
    return results
  except:
    raise Exception("Could not query members key")