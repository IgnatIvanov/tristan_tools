import os

def get_api_key() -> str:
    # file_path = os.path.join('services', 'ai_usage', 'access', 'openai_api_key.txt')
    file_path = os.path.abspath(os.path.join('services', 'ai_usage', 'access', 'openai_api_key.txt'))
    with open (file_path, 'r', encoding='utf-8') as f:
        key = f.read()
    return key
