import json
import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=1)

def get_user_memory(user_id: int):
    key = f"harvey:memory:{user_id}"
    data = r.get(key)
    return json.loads(data) if data else {}

def set_user_memory(user_id: int, memory: dict):
    key = f"harvey:memory:{user_id}"
    r.set(key, json.dumps(memory), ex=3600)  # expires in 1 hour

def clear_user_memory(user_id: int):
    r.delete(f"harvey:memory:{user_id}")
