import os
import json
from sqlalchemy import create_engine

def get_db_credentials():
    cred_path = os.path.join('services', 'arabica', 'access', 'db.json')
    with open(cred_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())

def get_engine():
    data = get_db_credentials()
    return create_engine(f'postgresql://{data['username']}:{data['password']}@{data['ip_addr']}:5432/{data['db_name']}')