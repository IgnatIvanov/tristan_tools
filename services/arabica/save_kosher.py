import os
import json
import hashlib
import psycopg2
from tqdm import tqdm
from datetime import datetime as dt
from psycopg2.extras import RealDictCursor, Json
from services.arabica.database import get_db_credentials

def get_dict_hash(d: dict) -> str:
    # 1. Сериализуем словарь в строку, гарантируя одинаковый порядок ключей
    # 2. Переводим строку в байты (.encode())
    serialized = json.dumps(d, sort_keys=True).encode('utf-8')    
    # 3. Считаем SHA-256 хеш и возвращаем его в виде строки
    return hashlib.sha256(serialized).hexdigest()

def ara_save_kosher_chat(
        chat: dict
):
    # Сохранение чата с клиентом из кошера
    chat_uuid = chat['conversation']['uuid']
    # engine = get_engine()
    
    # 
    creds = get_db_credentials()
    conn = psycopg2.connect(
        dbname=creds['db_name'],
        user=creds['username'], 
        password=creds['password'], 
        host=creds['ip_addr'], 
        port="5432"
    )
    # 
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        select_query = "SELECT * FROM kosher_chat WHERE uuid = %s;"
        cursor.execute(select_query, (chat_uuid,))
        chat_record = cursor.fetchone()
        # print('chat_record', chat_record)
        # print(chat_record is None)
    # 
    # Проверяем что чат не изменился, и обновлять не нужно
    # TODO
    chat_hash = get_dict_hash(chat)
    messages = sorted(chat['messages'], key=lambda item: item['created_at'])
    first_message_at = dt.fromisoformat(messages[0]['created_at']).replace(tzinfo=None)
    last_message_at = dt.fromisoformat(messages[-1]['created_at']).replace(tzinfo=None)
    do_action = 'ignore'
    if chat_record is None:
        do_action = 'create'
    else:
        record_last_msg_at = chat_record['last_message_at']
        if ((chat_record['chat_hash'] != chat_hash) or (record_last_msg_at < last_message_at)):
            do_action = 'update'
            
    match do_action:
        case 'ignore':
            return
        case 'create': 
            insert_query = """
                INSERT INTO kosher_chat (
                    uuid, sub_id, chat_json, chat_hash, analysis_json, need_analysis, 
                    first_message_at, last_message_at, last_message_text, 
                    first_name, last_name, username
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            try:
                with conn.cursor() as cursor:
                    cursor.execute(insert_query, (
                        chat_uuid,
                        chat['subscriber']['id'],
                        Json(chat),
                        chat_hash,
                        Json({}),  # analysis_json
                        False,  # need_analysis
                        first_message_at,
                        last_message_at,
                        messages[-1]['content'],  # last_message_text
                        chat['subscriber']['first_name'],
                        chat['subscriber']['last_name'],
                        chat['subscriber']['username'],
                    ))
                    generated_id = cursor.fetchone()[0]
                    conn.commit()
            except Exception as error:
                if 'conn' in locals() and conn:
                    conn.rollback()
                print(f"❌ Ошибка при добавлении данных: {error}")
            finally:
                if 'conn' in locals() and conn:
                    conn.close()

        case 'update':
            try:
                update_query = """
                    UPDATE kosher_chat 
                    SET 
                        chat_json = %s, 
                        chat_hash = %s, 
                        first_message_at = %s, 
                        last_message_at = %s, 
                        last_message_text = %s
                    WHERE uuid = %s;
                """
                with conn.cursor() as cursor:
                    cursor.execute(update_query, (
                        Json(chat),
                        chat_hash,
                        first_message_at,
                        last_message_at,
                        messages[-1]['content'],  # last_message_text
                        chat_uuid  # Идентификатор строки
                    ))
                    conn.commit()
            except Exception as error:
                if 'conn' in locals() and conn:
                    conn.rollback()
                print(f"❌ Ошибка при обновлении данных: {error}")
            finally:
                if 'conn' in locals() and conn:
                    conn.close()

if __name__ == '__main__':
    # chat_path = os.path.join('services', 'kosher', 'chats', '0b159cd4-6b63-4936-9018-32061a9b0083.json')
    chat_dir = os.path.join('services', 'kosher', 'chats')
    for chat_file in tqdm(os.listdir(chat_dir)):
        chat_path = os.path.join(chat_dir, chat_file)
        with open(chat_path, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        ara_save_kosher_chat(data)
