import os
# from pathlib import Path

def get_access_token():
    token_path = os.path.join('services', 'creative', 'access', 'bot_token.txt')
    with open (token_path, 'r', encoding='utf-8') as f:
        token = f.read()
    return token

if __name__ == '__main__':
    print(get_access_token())