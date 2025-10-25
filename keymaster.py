import garden
import random
import os
import math
import argparse
from art import text2art




def generate_keys(username, email, path):
  keys = garden.create_key_pair(username, email) 
  public_key = keys.pubkey
  try:
    os.makedirs(path)
  except FileExistsError:
    pass
  
  print("Saving keys in " + path)
  fp = open( path + "/pub.key", "w")
  fp.write(str(public_key))
  fp.close()

  fp = open(path + "/sec.key", "w")
  fp.write(str(keys))
  fp.close()
  print("Keys created!")



logo = text2art("Keymaster")
print(logo)
parser = argparse.ArgumentParser(prog="Key Generator")
parser.add_argument('path')
parser.add_argument('username')
parser.add_argument('email')
args = parser.parse_args()
generate_keys(args.username, args.email, args.path)