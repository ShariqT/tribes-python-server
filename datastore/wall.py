import redis
import uuid
import garden
import json
from . import pool
from datetime import timedelta

def get_current_wall():
  try:
    r = redis.Redis(connection_pool=pool)
    wall_keys = list(r.scan_iter(match="wall*"))
    current_wall = []
    print(f"these are the wall keys {wall_keys}")
    for key in wall_keys:
      current_wall.append(json.loads(r.get(key)))
    return current_wall
  except:
    return []


def create_wall_message(username, time_posted, text, link=None, image=None):
  try:
    r = redis.Redis(connection_pool=pool)
    wall_message = {
      "pk": uuid.uuid4().hex,
      "username": username,
      "data": {
        "link": link,
        "image": image,
        "text": text
      },
      "datetime": time_posted      
    }
    r.set(f"wall:{wall_message['pk']}", json.dumps(wall_message), ex=timedelta(minutes=30))
  except Exception as e:
    raise Exception(f"Could not post your message to the wall because {e}")


def create_topic(username, link, title, text, image=None):
  try:
    r = redis.Redis(connection_pool=pool)
    topic = {
      "pk": uuid.uuid4().hex,
      "username": username,
      "link": link,
      "title": title,
      "image": image,
      "text": text
    }
    r.set(f"topics:{topic['pk']}", json.dumps(topic), ex=timedelta(hours=2))
  except Exception as e:
    print(e)
    raise Exception(f"Could not create topic because {str(e)}")

def get_topics():
  try:
    r = redis.Redis(connection_pool=pool)
    topic_keys = list(r.scan_iter(match="topics*"))
    current_topics = []
    print(f"these are the topic keys {topic_keys}")
    for key in topic_keys:
      current_topics.append(json.loads(r.get(key)))
    print(current_topics)
    return current_topics
  except:
    raise Exception(f"Having trouble getting the current topics from this server")