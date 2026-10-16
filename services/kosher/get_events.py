import os
import json
import shutil
import random
import requests
import psycopg2
import pandas as pd
from tqdm import tqdm
from time import sleep
from datetime import datetime as dt, timedelta

from services.arabica.database import get_db_credentials
from scripts.kosher_load_data import get_kosher_auth_data

temp_save_path = os.path.join(os.getcwd(), 'services', 'kosher', 'temp_subs_and_events')

def load_kosher_clients(
        request_headers,
        session_cookies
):
    """Выгрузка данных о клиентах из Кошера с информацией об их конверсиях

    Args:
        request_headers (_type_): _description_
        session_cookies (_type_): _description_
    """    
    # временные файлы храним только за предыдущую выгрузку
    if os.path.exists(temp_save_path):
        shutil.rmtree(temp_save_path)
    os.makedirs(temp_save_path)
    # 
    # выгрузка
    current_page = 1
    while True:
        sleep(random.randint(3, 6))
        url = f"https://kosher-track.com/my/channels/2224/subscribers/data?page={current_page}&sort_by=joined_at&sort_direction=desc"
        response = requests.get(url, headers=request_headers, cookies=session_cookies)
        if response.status_code != 200:
            print(f"Ошибка {response.status_code}: {response.text}")
        save_path = os.path.join(temp_save_path, str(dt.now()).replace(':', '.')+'.json')
        data = response.json()
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, indent=4, ensure_ascii=False))
        if data['pagination']['last_page'] == current_page: break
        current_page += 1

def get_kosher_subs_events():
    # 
    # извлекаем события
    
    # Обработка файлов клиентов кошер
    print('Обработка файлов клиентов кошер')
    for file_name in tqdm(os.listdir(temp_save_path)):
        items = []
        
        file_path = os.path.join(temp_save_path, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())['data']
        for el in data:
            
            event = {
                'sub_id': el['id'],
                'chat_uuid': el['user_id'],
                'campaign_name': el['campaign_name'],
                'adset_name': el['adset_name'],
                'ad_name': el['ad_name'],
                'campaign_id': el['campaign_id'],
                'adset_id': el['adset_id'],
                'ad_id': el['ad_id'],
                'placement': el['placement'],
                'site_source_name': el['site_source_name'],
                'country_code': el['country_code'],
                # 'manager': item['manager'],
                # 'manager_name': manager_name, 
                # 'manager_from_messages': item['manager_from_messages'],
                'revenue': 0,
                'currency': 'USD',
            }
            
            # 
            # Добавление подписки
            # Время указано в часовом поясе +0
            # Для совпадения отображения с сайтом переводим всё на +3
            event_plus = event.copy()
            event_plus['type'] = 'subscription'
            event_plus['created_at'] = dt.fromisoformat(el['joined_at']) + timedelta(hours=3)
            items.append(event_plus)
            # 
            # Добавление отмены подписки
            # Время указано в часовом поясе +0
            # Для совпадения отображения с сайтом переводим всё на +3
            if el['unsubscribed_at'] is not None:
                event_plus = event.copy()
                event_plus['type'] = 'decline_subscription'
                event_plus['created_at'] = dt.fromisoformat(el['unsubscribed_at']) + timedelta(hours=3)
                items.append(event_plus)

        
        creds = get_db_credentials()
        conn = psycopg2.connect(
            dbname=creds['db_name'],
            user=creds['username'], 
            password=creds['password'], 
            host=creds['ip_addr'], 
            port="5432"
        )
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO kosher_event (sub_id, chat_uuid, fb_campaign_name, fb_adset_name, fb_ad_name,
            fb_campaign_id, fb_adset_id, fb_ad_id, placement, site_source_name,
            country_code, revenue, currency, event_type, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chat_uuid, created_at, event_type) 
            DO NOTHING;
        """
        events_df = pd.DataFrame(items)
        events_df.dropna(inplace=True, subset='created_at')
        
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
    request_headers, session_cookies = get_kosher_auth_data()
    load_kosher_clients(request_headers, session_cookies)
    get_kosher_subs_events()

if __name__ == '__main__':
    main()
    