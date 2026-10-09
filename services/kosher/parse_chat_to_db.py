import os
import ast
from tqdm import tqdm
import json
import pandas as pd
import psycopg2
from psycopg2.extras import register_default_jsonb
# 
from services.arabica.database import get_db_credentials
from services.arabica.save_kosher import ara_save_kosher_chat

def parse_chat_to_db(
        chat_path: str
):
    # Извлекаем события из файла чата
    with open(chat_path, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
    # сохранение данных чата из кошер в бд
    ara_save_kosher_chat(data)
    # 
    manager_from_messages = [json.dumps(m['manager'], indent=4, ensure_ascii=False) for m in data['messages']]
    manager_from_messages = list(set(manager_from_messages))
    # 
    item = {
        'chat_uuid': data['conversation']['uuid'],
        'sub_id': data['conversation']['subscriber_id'],
        'manager_id': data['conversation']['manager_id'],
        'manager': data['conversation']['manager'],
        'manager_from_messages': manager_from_messages, 
        'last_message_at': data['conversation']['last_message_at'],
        'conversation_created_at': data['conversation']['created_at'],
        'sales_status_id': data['conversation']['sales_status_id'],
        'country_code': data['subscriber']['country_code'],
        'subscribed_at': data['subscriber']['joined_at'],
        'unsubscribed_at': data['subscriber']['unsubscribed_at'],
        'campaign_id': data['subscriber']['campaign_id'],
        'adset_id': data['subscriber']['adset_id'],
        'ad_id': data['subscriber']['ad_id'],
        'campaign_name': data['subscriber']['campaign_name'],
        'adset_name': data['subscriber']['adset_name'],
        'ad_name': data['subscriber']['ad_name'],
        'placement': data['subscriber']['placement'],
        'site_source_name': data['subscriber']['site_source_name'],
        'deposits': data['subscriber']['deposits'],
        'tags': data['subscriber']['tags'],
    }

    item['manager_from_messages'] = [el for el in item['manager_from_messages'] if el != 'null']
    # if item['manager_from_messages']:
    #     print("type(item['manager_from_messages'])", type(item['manager_from_messages']))
    #     print("type(item['manager_from_messages'][0])", type(item['manager_from_messages'][0]))
    #     # print('manager_from_messages', r['manager_from_messages'])
    #     # print('manager_from_messages', type(r['manager_from_messages']))
    #     # manager_from_messages = r['manager_from_messages'].replace("'", '"')
    #     item['manager_from_messages'] = ast.literal_eval(item['manager_from_messages'])
    #     if type(item['manager_from_messages']) == float: item['manager_from_messages'] = []
    #     item['manager_from_messages'] = [el for el in item['manager_from_messages'] if el != 'null']
    # 
    if type(item['manager']) == float: item['manager'] = None
    manager_name = 'не указан'
    if item['manager']:
        # item['manager'] = ast.literal_eval(item['manager'])
        # print("r['manager']", r['manager'])
        manager_name = item['manager']['name']
    elif item['manager_from_messages']:
        if len(item['manager_from_messages']) > 0:
            item['manager_from_messages'] = json.loads(item['manager_from_messages'][0])
            # print('manager_from_messages', r['manager_from_messages'])
            # print('manager_from_messages', type(r['manager_from_messages']))
            manager_name = item['manager_from_messages']['name']
            # my_count += 1
    else:
        manager_name = 'не указан'
    # 
    if item['country_code']:
        item['country_code'] = str(item['country_code']).upper()
    # 
    # 
    events = []
    # if manager_name is None: manager_name = 'не указан'
    # print('manager_name', manager_name)
    event = {
        'sub_id': item['sub_id'],
        'chat_uuid': item['chat_uuid'],
        'campaign_name': item['campaign_name'],
        'adset_name': item['adset_name'],
        'ad_name': item['ad_name'],
        'campaign_id': item['campaign_id'],
        'adset_id': item['adset_id'],
        'ad_id': item['ad_id'],
        'placement': item['placement'],
        'site_source_name': item['site_source_name'],
        'country_code': item['country_code'],
        'manager': item['manager'],
        'manager_name': manager_name, 
        'manager_from_messages': item['manager_from_messages'],
        'revenue': 0,
        'currency': 'USD',
    }
    # # 
    # # Добавление подписки
    # event_plus = event.copy()
    # event_plus['type'] = 'subscription'
    # event_plus['created_at'] = item['subscribed_at']
    # events.append(event_plus)
    # # 
    # # Добавление отмены подписки
    # event_plus = event.copy()
    # event_plus['type'] = 'decline_subscription'
    # event_plus['created_at'] = item['unsubscribed_at']
    # events.append(event_plus)
    # 
    # Добавление диалога
    event_plus = event.copy()
    event_plus['type'] = 'dialog'
    event_plus['created_at'] = item['conversation_created_at']
    events.append(event_plus)
    # 
    # Добавление события отмены подписки
    # item['tags'] = json.loads(item['tags'])
    reg_tag = next((d for d in item['tags'] if d.get('system_event') == 'Registration'), None)
    if reg_tag:
        event_plus = event.copy()
        event_plus['type'] = 'registration'
        event_plus['created_at'] = reg_tag['pivot']['created_at']
        events.append(event_plus)
    # 
    # Добавление событий покупок
    # item['deposits'] = ast.literal_eval(item['deposits'])
    for el in item['deposits']:
        # print("r['deposits']", r['deposits'])
        event_plus = event.copy()
        event_plus['type'] = 'deposit'
        event_plus['revenue'] = el['amount']
        event_plus['currency'] = el['currency']
        event_plus['created_at'] = el['created_at']
        events.append(event_plus)
    # 
    # Добавление события первого депозита
    if len(item['deposits']) > 0:
        ftd_item = item['deposits'][0]
        event_plus = event.copy()
        event_plus['type'] = 'ftd'
        event_plus['revenue'] = ftd_item['amount']
        event_plus['currency'] = ftd_item['currency']
        event_plus['created_at'] = ftd_item['created_at']
        events.append(event_plus)
    # 
    events_df = pd.DataFrame(events)
    events_df.dropna(inplace=True, subset='created_at')
    # 
    creds = get_db_credentials()
    conn = psycopg2.connect(
        dbname=creds['db_name'],
        user=creds['username'], 
        password=creds['password'], 
        host=creds['ip_addr'], 
        port="5432"
    )
    register_default_jsonb(conn_or_curs=conn)
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO kosher_event (sub_id, chat_uuid, fb_campaign_name, fb_adset_name, fb_ad_name,
        fb_campaign_id, fb_adset_id, fb_ad_id, placement, site_source_name,
        country_code, manager, manager_name, manager_from_messages,
        revenue, currency, event_type, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (chat_uuid, created_at, event_type) 
        DO NOTHING;
    """
    events_df = events_df[['sub_id', 'chat_uuid', 'campaign_name', 'adset_name', 'ad_name',
       'campaign_id', 'adset_id', 'ad_id', 'placement', 'site_source_name',
       'country_code', 'manager', 'manager_name', 'manager_from_messages',
       'revenue', 'currency', 'type', 'created_at']]
    try:
        # 4. Преобразуем строки DataFrame в список кортежей и отправляем пачкой
        # to_numpy() преобразует данные в удобный для psycopg2 формат строк/колонок
        records_to_insert = []
        for row in events_df.to_numpy():
            clean_row = []
            for item in row:
                # Если элемент является списком или словарем — принудительно переводим в валидную JSON-строку
                if isinstance(item, (dict, list)):
                    clean_row.append(json.dumps(item, ensure_ascii=False))
                else:
                    clean_row.append(item)
            records_to_insert.append(tuple(clean_row))
        
        cursor.executemany(insert_query, records_to_insert)
        
        # 5. Фиксируем транзакцию
        conn.commit()
        # print(f"Успешно обработано строк: {len(events_df)}")

    except Exception as error:
        print(f"Ошибка при работе с PostgreSQL: {error}")
        conn.rollback()
        
    finally:
        # 6. Закрытие курсора и соединения
        cursor.close()
        conn.close()

def main():
    chats_dir = os.path.join('services', 'kosher', 'chats')
    for chat_file in tqdm(os.listdir(chats_dir)):
        parse_chat_to_db(os.path.join(chats_dir, chat_file))

if __name__ == '__main__':
    main()
