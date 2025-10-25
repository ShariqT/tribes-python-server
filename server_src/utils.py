from datastore import messages as server_messages
import datastore



def create_server_message(message_text, selected_mod, admin_username, server_publickey, admin_key):
  new_message = server_messages.ServerMessage(request.form['text'])
  new_message.from_fingerprint = admin_key.fingerprint
  new_message.from_username = admin_username
  new_message.to_fingerprint = selected_mod['fingerprint']
  new_message.to_username = selected_mod['username']
  new_message.create_message(server_publickey)



# def check_blocked_list(requestor_key):
#   return datastore.is_key_blocked(requestor_key)
