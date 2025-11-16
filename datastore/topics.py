import redis
import uuid
import garden
import json
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from . import pool
from datetime import timedelta

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