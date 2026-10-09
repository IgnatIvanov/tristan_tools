import os
import json

def get_auth_data():
    cred_path = os.path.join('services', 'kosher', 'access', 'user_auth_data.json')
    with open(cred_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())
