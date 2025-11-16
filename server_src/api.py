from flask import Blueprint, request, render_template
from flask.json import jsonify
import datastore
from datastore import topics
import garden
import json
from datastore import access as access_request
from datastore import wall
import os
from dotenv import load_dotenv
import markdown

load_dotenv()
clientAPI = Blueprint('clientAPI', __name__)

@clientAPI.route("/open_door_policy", methods=["GET"])
def get_open_door_policy():
  access_level = os.getenv('PUBLIC_ACCESS', '0')
  if access_level == '1':
    return jsonify({"open": 1 })
  return jsonify({"open": 0})

@clientAPI.route("/block", methods=["POST"])
def check_blocked():
  requestor_key = garden.create_key_from_text(request.form['key'])
  try:
    if datastore.is_key_blocked(requestor_key) == True:
      return jsonify({ "blocked": True })
    return jsonify({ "blocked": False })
  except Exception as e:
    return jsonify({ "error": f"There was an error checking the block list: {str(e)}"})

@clientAPI.route("/connect", methods=["POST"])
def connect_server():
  requestor_key = garden.create_key_from_text(request.form['key'])
  try:
    print(os.environ)
    access_level = os.getenv('PUBLIC_ACCESS', '0')
    if access_level == '1':
      # check the blocked list
      if datastore.is_key_blocked(requestor_key) == True:
        return jsonify({ "access_allowed": False })
      else:
        return jsonify({ "access_allowed": True })
    else:
      results = datastore.search_member(requestor_key)
      if len(results) == 0:
        return jsonify({"access_allowed": False})
      return jsonify({ "access_allowed": True })
  except Exception as e:
    # TODO: make classes for possible exceptions to better filter
    return jsonify({ "error": f"I couldn't figure out access rules for the server because of this error: {str(e)}"})

@clientAPI.route("/topic_list", methods=["POST"])
def process_command():
  requestor_key = garden.create_key_from_text(request.form['key'])
  access_level = os.getenv('PUBLIC_ACCESS', '0')
  try:
    if access_level == '1':
      # check the blocked list
      if datastore.is_key_blocked(requestor_key) == True:
        return jsonify({ "access_allowed": False })
      else:
        current_topics = topics.get_topics()
        return jsonify({ "topics": current_topics })
    else:
      results = datastore.search_member(requestor_key)
      if len(results) == 0:
        return jsonify({"error": "Hey, you are not allowed to look at the topics for this server anymore. You probably got blocked."})
      current_topics = topics.get_topics()
      return jsonify({ "topics": current_topics })
  except Exception as e:
    print(e)
    return jsonify({"error": "Aye! I can't get the current topics from this server. Shit is fucked up. If it keeps happening, contact the server admin."})
  

@clientAPI.route("/topic_create", methods=["POST"])
def create_topic():
  data = json.loads(request.form['values'])
  key = request.form['key']
  pubkey = garden.create_key_from_text(request.form['key'])
  username = garden.generate_key_name_id(pubkey)
  try:
    if datastore.is_key_blocked(pubkey) == True:
      return jsonify({ "access_allowed": False })

    link = None
    if data['link'] != "":
      link = data['link']
    topics.create_topic(username, data['link'], data['title'], data['text'], link)
    return jsonify({"success": True})
  except Exception as e:
    return jsonify({"error": f"I couldn't create the topic. {str(e)}"})


@clientAPI.route("/request_access", methods=['POST'])
def request_access():
  try:
    pubkey = garden.create_key_from_text(request.form['key'])
    username = garden.generate_key_name_id(pubkey)
    if datastore.is_key_blocked(pubkey) == True:
      return jsonify({ "error": f"You have been blocked from this server" })
    access_request.create_request_access_message(username, pubkey.fingerprint, pubkey)
    return jsonify({"success": True })
  except Exception as e:
    return jsonify({"error": f"There was an error creating this access request. {str(e)}"})

@clientAPI.route("/mymessages", methods=["POST"])
def get_messages_by_key():
  try:
    pubkey = garden.create_key_from_text(request.form['key'])
    username = garden.generate_key_name_id(pubkey)
    pubkey_messages = messages.get_messages_by_key(pubkey)
    return jsonify({"messages": pubkey_messages })
  except Exception as e:
    return jsonify({"error": f"There was an error reterving messages for you: {str(e)}"})

@clientAPI.route("/wall", methods=['POST'])
def get_current_wall():
  try:
    requestor_key = garden.create_key_from_text(request.form['key'])
    results = datastore.search_member(requestor_key)
    if len(results) == 0:
      return jsonify({"error": f"You dont have permission to view the wall"})
    results = wall.get_current_wall()
    return jsonify({"wall": results })
  except Exception as e:
    return jsonify({"error": f"Could not get the current state of the wall becase {e}"})

@clientAPI.route("welcome", methods=['POST'])
def publish_welcome_message():
  try:
    requestor_key = garden.create_key_from_text(request.form['key'])
    access_level = os.getenv('PUBLIC_ACCESS', '0')
    if access_level == '1':
      if os.path.exists("./server_src/templates/welcome_public.md") is True:
        fp = open("./server_src/templates/welcome_public.md")
        welcome_message = markdown.markdown(fp.read())
      else:
        welcome_message = "Welcome to my server"
    else:
      if os.path.exists("../templates/welcome_member.md") is True:
        fp = open("../templates/welcome_member.md")
        welcome_message = markdown.markdown(fp.read())
      else:
        welcome_message = "Welcome, member of our server! I will be updating this with information pertaining to our members."
    return jsonify({"welcome": welcome_message })
  except Exception as e:
    return jsonify({"error": f"Cannot send the welcome message: {str(e)}"})


@clientAPI.route("/wall_post", methods=['POST'])
def post_new_wall_message():
  try:
    requestor_key = garden.create_key_from_text(request.form['key'])
    results = datastore.search_member(requestor_key)
    if len(results) == 0:
      return jsonify({"error": f"You dont have permission to view the wall"})
    wall.create_wall_message(
      garden.generate_key_name_id(requestor_key),
      request.form['time_posted'],
      request.form['text'],
      request.form['link'],
      request.form['image']
    )
    results = wall.get_current_wall()
    return jsonify({ "wall": results })
  except Exception as e:
    print(e)
    return jsonify({ "error": "Oops! Error on the server; could not post your wall message!"})
    
