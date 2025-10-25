

import json
import pickle
import garden
import argparse
import redis
import subprocess
import datastore

parser = argparse.ArgumentParser(prog="Secret Garden Server", description="Secret Garden Server Admin")
parser.add_argument("--check-db-connection", action='store_true')
parser.add_argument("--setup-db", action='store_true')
parser.add_argument("--add-superuser")
parser.add_argument('--run-server', action='store_true')
parser.add_argument('--port', type=int)

args = parser.parse_args()
print(args)
r = redis.Redis(host='localhost', port=6380, db=0, protocol=3, decode_responses=True)

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
  datastore.messages.create_message_index()
  print("Created people indexes")
  print("Created message index")
  print("You can now add a superuser to this server!")

if args.add_superuser is not None:
  keyfile = open(args.add_superuser)
  keydata = keyfile.read()
  superuser_key = garden.create_key_from_text(keydata)
  name_id = garden.generate_key_name_id(superuser_key)
  # superuser_key_users = superuser_key.userids
  # print(superuser_key.fingerprint[-8:])
  # name_id = superuser_key_users[0].name + "-" + superuser_key.fingerprint[-8:]
  r.set("superuser_username", name_id)
  r.set("superuser", keydata)
  print(f"Saved public key in {args.add_superuser} to the superuser of this server")
  r.close()
  exit()

# TODO: Add the dotenv package to get the env variables for
# the databse logins/host and the host and ports to serve the flask app on
# also put in the production version of this call which will call waitress, 
# which is already installed. 
if args.run_server is True:
  subprocess.call("flask --app server_src --debug run --port 8080", shell=True)



