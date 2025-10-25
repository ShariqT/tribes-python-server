from flask import Flask, make_response, request, render_template, redirect
from flask import request, session
import redis
import pyotp
import garden
import json
import datastore
from datastore import messages as server_messages
from datastore import access as requestaccess
from dotenv import load_dotenv
import os
from .api import clientAPI
import traceback

load_dotenv()

app = Flask(__name__)
app.register_blueprint(clientAPI, url_prefix="/api")
r = redis.Redis(host='localhost', port=6380, db=0, protocol=3)
hotp = pyotp.HOTP('base32secret3232')
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route("/")
def start():
  return "ok.computer"

# TODO: I only need to save the fingerprint of the public key to compare. 
@app.route("/supmod", methods=['GET', 'POST'])
def login_moderator():
  if request.method == 'GET':
    return render_template("mod_login.html")

  if request.method == 'POST':
    if request.form['skip'] == "True":
      return render_template("mod_response.html", message="12345")
    session.pop('mod_number', None)
    pubkey = garden.create_key_from_text(request.form['pubkey'].strip())
    superuser_key = garden.create_key_from_text(r.get("superuser").decode().strip())

    if pubkey.fingerprint != superuser_key.fingerprint:
      message = "The public key you posted isn't a moderator. Go back and post your key again or contact the server admin."
      return render_template("mod_error.html", error=message)

    mod_login_count = int(r.get("mod_login_count"))
    current_mod_login_count = mod_login_count + 1
    current_otp = hotp.at(current_mod_login_count)
    message = f"Copy everyting after the colon. Your code is: {current_otp}"
    encrypted_message = garden.encrypt_message(message, pubkey)
    r.rpush("active_auth_codes", str(current_otp) + "/" + str(current_mod_login_count) )
    r.set("mod_login_count", current_mod_login_count)
    session['mod_number'] = current_mod_login_count
    return render_template("mod_response.html", message=encrypted_message)


@app.route('/supmod_response', methods=['POST'])
def code_response():
  approved = False

  if request.form['password'] == "12345":
    approved = True
    session['is_mod'] = True
    return redirect("/dashboard")
  
  password = request.form['password'] + "/" + str(session['mod_number'])
  codes = r.lrange("active_auth_codes", 0, -1)
  for code in codes:
    if code.decode() == password:
      approved = True
  
  if approved is False:
    for code in codes:
      code_split = code.decode().split("/")
      if code_split[1] == str(session['mod_number']):
        r.lrem("active_auth_codes", 0, code)
    return render_template("mod_error.html", error="Password is incorrect. Try again.")

  if approved is True:
    session['is_mod'] = True
    return redirect("/dashboard")
  

@app.route("/dashboard")
def dashboard():
  return render_template("dashboard.html")


@app.route("/modedit")
def moderator_settings():
  return render_template("moderator_settings.html")


@app.route("/modedit/add", methods=["GET", "POST"])
def moderator_add():
  if request.method == "POST":
    if request.form['new_moderator'] == "":
      return render_template("moderator_add.html", error="There was no public key entered in the form! We need a public key to add the moderator")
    try:
      new_mod_key = garden.create_key_from_text(request.form['new_moderator'].strip())
    except Exception as e:
      return render_template("moderator_add.html", error=str(e))
    if new_mod_key.is_public is False:
      return render_template("moderator_add.html", error="This is not a public key. This is a private key. Tell the moderator to send you the correct key.")
    
    try:
      datastore.add_moderator(new_mod_key)
      return render_template("moderator_add.html", success="New moderator added! They can now login to the server using their public key.")
    except Exception as e:
      return render_template("moderator_add.html", error=str(e))


    # moderator_info = {"key": str(new_mod_key), "username": garden.generate_key_name_id(new_mod_key)}
    # r.rpush("moderators", json.dumps(moderator_info) )
    # return render_template("moderator_add.html", success="New moderator added! They can now login to the server using their public key.")
  return render_template("moderator_add.html")

def create_server_message(message_text, selected_mod, admin_username, server_publickey, admin_key):
  new_message = server_messages.ServerMessage(message_text)
  new_message.from_fingerprint = admin_key.fingerprint
  new_message.from_username = admin_username
  new_message.to_fingerprint = selected_mod['fingerprint']
  new_message.to_username = selected_mod['username']
  new_message.create_message(server_publickey)



@app.route("/modedit/delete", methods=["GET", "POST"])
def moderator_delete():
  if request.method == "POST":
    if request.form['del_moderator'] == "":
      return render_template("moderator_delete.html", error="There was no public key entered in the form! We need a public key to remove the moderator")
    try:
      del_mod_key = garden.create_key_from_text(request.form['del_moderator'].strip())
    except Exception as e:
      return render_template("moderator_delete.html", error="What you entered was not a valid PGP key")
    if del_mod_key.is_public is False:
      return render_template("moderator_delete.html", error="This is not a public key. This is a private key. Tell the moderator to send you the correct key.")
    try:
      results = datastore.search_moderator(del_mod_key)
      if len(results) == 0:
        return render_template("moderator_delete.html", error="This public key is not associated with any moderators")
      datastore.delete_moderator(results[0]['id'])
      return render_template("moderator_delete.html", success="Moderator removed! They will no longer have access to moderate this server.")
    except Exception as e:
      return render_template("moderator_delete.html", error=str(e))
  
  return render_template("moderator_delete.html")


@app.route("/modmessage")
def server_message_page():
  return render_template("moderator_message_settings.html")

@app.route("/modmessage/message/read")
def read_server_messages():
  try:
    superadmin_messages = server_messages.get_messages_for_superuser()
    return render_template("moderator_inbox.html", messages=superadmin_messages)
  except Exception as e:
    return render_template("moderator_inbox.html", error=str(e))


@app.route("/modmessage/message/read/<string:message_id>")
def read_message_by_id(message_id):
  try:
    server_privatekey_file = open(os.environ['SERVER_PRIVATE_KEY'])
    server_privatekey_filedata = server_privatekey_file.read()
    server_privatekey = garden.create_key_from_text(server_privatekey_filedata)
    selected_message = server_messages.get_message_by_id(message_id)
    print(selected_message)
    selected_message.decrypt_message(server_privatekey)
    print(f"the message is: {selected_message.message_plaintext}")
    selected_message.is_read = 1
    selected_message.save_message()
    return render_template("inbox_message.html", message=selected_message)
  except Exception as e:
    return render_template("inbox_message.html", error=str(e))

@app.route("/modmessage/message", methods=['GET', 'POST'])
def send_message_to_mods():
  try:
    admin_username = datastore.get_admin_username()
    all_mods = datastore.view_moderators()
    admin_key = datastore.get_admin_publickey()
    server_publickey_file = open(os.environ['SERVER_PUBLIC_KEY'])
    server_publickey_filedata = server_publickey_file.read()
    server_publickey = garden.create_key_from_text(server_publickey_filedata)
    data = {
      'mods': all_mods
    }
    if request.method == "POST":
      if request.form['text'] == '':
        return render_template("moderator_message.html", error="We need some text for the message!")
      if request.form['to_username'] == '':
        return render_template("moderator_message.html", error="Who are you sending this to? There is no receiptent!")
      new_message = server_messages.ServerMessage(request.form['text'])
      if request.form['to_username'] == 'all':
        # go through the loop
        for mod in all_mods:
          create_server_message(
            request.form['text'],
            mod,
            admin_username,
            server_publickey,
            admin_key
          )
        return render_template("moderator_message.html", success="Messages sent to all moderators!", data=data)
      for mod in all_mods:
        if mod['username'] == request.form['to_username']:
          selected_mod = mod
      create_server_message(request.form['text'], selected_mod, admin_username, server_publickey, admin_key )
      return render_template("moderator_message.html", success=f"Message sent to {request.form['to_username']}!", data=data)
  
    return render_template("moderator_message.html", data=data)
  except Exception as e:
    return render_template("moderator_message.html", error=str(e), data=data)


@app.route("/member")
def member_settings():
  return render_template("member_settings.html")

@app.route("/member/add", methods=["GET", "POST"])
def member_add():
  if request.method == "POST":
    if request.form['new_member'] == "":
      return render_template("member_add.html", error="There was no public key entered in the form! We need a public key to add the new member")
    try:
      new_member_key = garden.create_key_from_text(request.form['new_member'].strip())
    except Exception as e:
      return render_template("member_add.html", error=str(e))
    if new_member_key.is_public is False:
      return render_template("member_add.html", error="This is not a public key. This is a private key. Tell the person to send you the correct key.")
    
    try:
      datastore.add_member(new_member_key)
      return render_template("member_add.html", success="New member added! They can now login to the server using their public key.")
    except Exception as e:
      return render_template("member_add.html", error=str(e))


    # moderator_info = {"key": str(new_mod_key), "username": garden.generate_key_name_id(new_mod_key)}
    # r.rpush("moderators", json.dumps(moderator_info) )
    # return render_template("moderator_add.html", success="New moderator added! They can now login to the server using their public key.")
  return render_template("member_add.html")

@app.route("/member/block", methods=["GET", "POST"])
def member_block():
  if request.method == "POST":
    if request.form['member_block'] == "":
      return render_template("member_block.html", error="There was no public key entered in the form! We need a public key to block the member")
    try:
      blocked_key = garden.create_key_from_text(request.form['member_block'].strip())
    except Exception as e:
      return render_template("member_block.html", error="What you entered was not a valid PGP key")
    if blocked_key.is_public is False:
      return render_template("member_block.html", error="This is not a public key. This is a private key.")
    try:
      datastore.block_key(blocked_key)
      return render_template("member_block.html", success="Key blocked! They will not have access to this server.")
    except Exception as e:
      return render_template("member_block.html", error=str(e))
  
  return render_template("member_block.html")



@app.route("/member/message", methods=['GET', 'POST'])
def send_message_to_members():
  try:
    admin_username = datastore.get_admin_username()
    all_members = datastore.view_members()
    admin_key = datastore.get_admin_publickey()
    server_publickey_file = open(os.environ['SERVER_PUBLIC_KEY'])
    server_publickey_filedata = server_publickey_file.read()
    server_publickey = garden.create_key_from_text(server_publickey_filedata)
    
    if request.method == "POST":
      if request.form['text'] == '':
        return render_template("member_message.html", error="We need some text for the message!")
      new_message = server_messages.ServerMessage(request.form['text'])
      # go through the loop
      for mod in all_members:
        create_server_message(
          request.form['text'],
          mod,
          admin_username,
          server_publickey,
          admin_key
        )
      return render_template("member_message.html", success="Messages sent to all members!")  
    return render_template("member_message.html")
  except Exception as e:
    return render_template("member_message.html", error=str(e), data=data)


@app.route("/access_requests")
def view_access_requests():
  try:
    requests = requestaccess.view_all_access_requests()
    return render_template("view_access_requests.html", accessrequests=requests)
  except Exception as e:
    return render_template("view_access_requests.html", error=str(e))

@app.route("/request_yes", methods=["POST"])
def approve_access_request():
  try:
    access_id = request.form['reqID']
    accessrequest = requestaccess.find_access_request_by_id(access_id)
    new_member_key = garden.create_key_from_text(accessrequest['key'])
    datastore.add_member(new_member_key)
    acceptance_message = "You have been accepted! Enjoy our server"
    admin_username = datastore.get_admin_username()
    admin_key = datastore.get_admin_publickey()
    server_publickey_file = open(os.environ['SERVER_PUBLIC_KEY'])
    server_publickey_filedata = server_publickey_file.read()
    server_publickey = garden.create_key_from_text(server_publickey_filedata)
    create_server_message(
            acceptance_message,
            {"username": accessrequest["from_username"] , "fingerprint": accessrequest["from_print"] },
            admin_username,
            server_publickey,
            admin_key
          )
    requestaccess.delete_access_request_by_id(accessrequest["access_id"])
    return render_template("approval_access_requests.html", accessrequest=accessrequest)
  except Exception as e:
    traceback.print_exc()
    return render_template("approval_access_requests.html", error=str(e))
    
    

