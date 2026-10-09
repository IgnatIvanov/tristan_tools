import os
import json

def get_chat_content(uuid: str) -> dict:
    # chats_dir = os.path.abspath(os.path.join('..', 'services', 'kosher', 'chats'))
    chats_dir = os.path.join('services', 'kosher', 'chats')
    chat_path = os.path.join(chats_dir, uuid + '.json')
    with open(chat_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())
