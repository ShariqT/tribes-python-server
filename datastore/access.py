import redis
import uuid
import garden
import json
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query, NumericFilter
from . import pool

request_access_schema = (
  TextField("$.access_id", as_name="access_id"),
  TextField("$.from_print", as_name="from_print"), # pgp fingerprint
  TextField("$.from_username", as_name="from"),
  TextField("$.key", as_name="key"),
  TextField("$.approval_status", as_name="read") # 0 or 1
)

def create_request_access_index():
  try:
    r = redis.Redis(connection_pool=pool)
    r.ft("idx:access_requestsv2").create_index(
      request_access_schema,
      definition=IndexDefinition(
          prefix=["access_requestsv2:"], index_type=IndexType.JSON
      )
    )
    r.close()
  except:
    raise Exception(f"Could not create request access index")


def update_approval_by_access_id(access_id, approval_status):
  try:
    r = redis.Redis(connection_pool=pool)
    r.json().set(f"access_requestsv2:{access_id}", "$.approval_status", approval_status)
  except:
    raise Exception(f"Could not update request apporval for id {access_id}")

def delete_access_request_by_id(access_id):
  try:
    r = redis.Redis(connection_pool=pool)
    r.delete(f"access_requestsv2:{access_id}")
  except:
    raise Exception("Could not delete access request")
def find_access_request_by_id(access_id):
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:access_requestsv2").search(Query(f"@access_id:{access_id}"))
    if len(query_results['results']) == 0:
      raise Exception(f"There is no such message with id {access_id}")
    return json.loads(query_results['results'][0]['extra_attributes']['$'])
  except:
    raise Exception(f"Could not get info for message {access_id}")

def create_request_access_message(requestor_username, requestor_fingerprint, requestor_public_key):
  try:
    access_id = uuid.uuid4().hex
    r = redis.Redis(connection_pool=pool)
    r.json().set(f"access_requestsv2:{access_id}", Path.root_path(), {
      "access_id": access_id,
      "from_print": requestor_fingerprint,
      "from_username": requestor_username,
      "key": str(requestor_public_key),
      "approval_status": 'N'
    })
    r.close()
  except Exception as e:
    print(e)
    raise Exception("Access request could not be created. Try again, if and if it still doesnt work, then contact the server admin.")


def view_all_access_requests():
  try:
    r = redis.Redis(connection_pool=pool)
    query_results = r.ft("idx:access_requestsv2").search(Query("*"))
    r.close()
    if len(query_results['results']) == 0:
      return []
    returned_access_requests = []
    for result in query_results['results']:
      returned_access_requests.append(json.loads(result['extra_attributes']['$']))
    return returned_access_requests
  except Exception as e:
    raise Exception(f"Tried to get your server's access requests but ran into an error {str(e)}")



