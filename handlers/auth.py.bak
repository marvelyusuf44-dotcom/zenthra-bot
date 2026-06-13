import json
import os
from datetime import datetime
from config import USERS_FILE

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def is_allowed(user_id):
    users = load_users()
    if str(user_id) in users:
        expired = users[str(user_id)].get('expired')
        if expired and datetime.now() > datetime.fromisoformat(expired):
            return False
        return True
    return False

def is_admin(user_id):
    from config import ADMIN_ID
    return user_id == ADMIN_ID
