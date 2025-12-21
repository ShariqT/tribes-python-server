

import json
import pickle
import garden
import argparse
import redis
import subprocess
import datastore
from datastore import messages
from dotenv import load_dotenv
import os
load_dotenv()

parser = argparse.ArgumentParser(prog="Secret Garden Server", description="Secret Garden Server Admin")
parser.add_argument("--check-db-connection", action='store_true')
parser.add_argument("--setup-db", action='store_true')
parser.add_argument("--add-superuser")
parser.add_argument('--run-dev-server', action='store_true')
parser.add_argument('--run-server', action='store_true')
# parser.add_argument('--port', type=int, default=8080)

args = parser.parse_args()
r = redis.Redis(host=os.environ['REDIS_HOST'], 
    port=os.environ['REDIS_PORT'], 
    db=os.environ['REDIS_DB'],
    username=os.environ['REDIS_USERNAME'],
    password=os.environ['REDIS_PASSWORD'],
    protocol=3, 
    decode_responses=True
)

if args.check_db_connection is True:
  try:
    r.ping()
    print("Db connected!")
    exit()
  except Exception as e:
    print("Could not connect to database: " + str(e))
    exit()

if args.setup_db is True:
  r.set("mod_login_count", 150)
  r.rpush("active_auth_codes", "start")
  datastore.create_people_index()
  datastore.create_people_index("moderators")
  datastore.create_people_index("blocked")
  messages.create_message_index()
  print("Created people indexes")
  print("Created message index")
  print("Created blocked index")
  print("You can now add a superuser to this server!")
  r.close()

if args.add_superuser is not None:
  keyfile = open(os.environ['ADMIN_KEY'])
  keydata = keyfile.read()
  superuser_key = garden.create_key_from_text(keydata)
  name_id = garden.generate_key_name_id(superuser_key)
  r.set("superuser_username", name_id)
  r.set("superuser", keydata)
  print(f"Saved public key in {args.add_superuser} to the superuser of this server")
  r.close()
  exit()


if args.run_dev_server is True:
  os.environ['MODE'] = 'DEBUG'
  subprocess.call(f"flask --app server_src --debug run --port {os.environ['PORT']}", shell=True)

if args.run_server is True:
  from waitress import serve
  from server_src import app
  os.environ['MODE'] = 'PROD'
  print(f"Running production server on port {os.environ['PORT']}")
  serve(app, host='0.0.0.0', port=os.environ['PORT'])




