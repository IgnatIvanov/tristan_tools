import os
import json
import random
import requests
import traceback
from tqdm import tqdm
from time import sleep
from datetime import datetime as dt, timezone
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import platform
# 
from services.kosher.access.auth import get_auth_data
from services.kosher.tasks import get_last_load_dt
from services.kosher.tasks import set_last_load_dt
from services.kosher.tasks import add_chat_to_load
from services.kosher.tasks import get_chats_to_load as get_chats_uuids
from services.kosher.tasks import rewrite_chats_to_load
from scripts.create_out_reports import main as create_reports
from services.google.send import main as send_reports_to_gdrive
from services.kosher.parse_chat_to_db import parse_chat_to_db
# 
uc_kosher_profile_path = os.path.join(os.getcwd(), 'services', 'kosher', 'uc_kosher_profile')
chats_dir = os.path.join(os.getcwd(), 'services', 'kosher', 'chats')

def pass_login_page(
        driver: uc.Chrome
):
    wd = WebDriverWait(driver, 45)
    email_field = wd.until(EC.element_to_be_clickable((By.ID, "email")))
    password_field = driver.find_element(By.ID, "password")
    # 
    auth_data = get_auth_data()
    # Определяем клавишу-модификатор в зависимости от ОС (Ctrl для Windows/Linux, Command для Mac)
    modifier_key = Keys.COMMAND if platform.system() == 'Darwin' else Keys.CONTROL
    
    # Выделяем весь текст и удаляем его
    email_field.send_keys(modifier_key + "a")
    email_field.send_keys(Keys.BACKSPACE)
    email_field.send_keys(auth_data['username'])
    sleep(random.uniform(4.0, 6.0))
    password_field.send_keys(modifier_key + "a")
    password_field.send_keys(Keys.BACKSPACE)
    password_field.send_keys(auth_data['password'])
    sleep(random.uniform(4.0, 6.0))
    # 
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Войти')]")
    login_button.click()
    sleep(15)

def get_kosher_auth_data():
    
    # options = uc.ChromeOptions()
    # Включаем логирование производительности
    # options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    # 
    # user_profile_path = os.path.join(os.getcwd(), 'uc_kosher_profile')
    # 
    for version in [154, 153, 152, 151]:
        try:
            print('Trying chrome version', version)
            options = uc.ChromeOptions()
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            driver = uc.Chrome(
                version_main=version,
                options=options,
                # user_data_dir=uc_kosher_profile_path,
            )
            break
        except Exception as e:  
            print(f"Ошибка при запуске Chrome: {e}")
            traceback.print_exc()  
            continue 
            driver = uc.Chrome(
                version_main=151,
                options=options,
                user_data_dir=uc_kosher_profile_path,
            )

    goto_url = "https://kosher-track.com/messenger-v2/chats?channel_id=2224&cc_id=27"
    goto_url_2 = "https://kosher-track.com/messenger-v2/chats?cc_id=27&channel_id=2224"
    driver.get(goto_url)
    sleep(10)
    # driver.get("https://kosher-track.com/my")
    # driver.get("https://kosher-track.com/account/sign-in")
    # driver.save_screenshot("cloudflare_test.png")
    # driver.quit()
    while driver.current_url != goto_url:
        if driver.current_url == goto_url: break
        if driver.current_url == goto_url_2: break
        sleep(10)
        if 'sign-in' in driver.current_url: pass_login_page(driver)
    # 

    # Получение cookie 
    # cookies = driver.get_cookies()
    session_cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}

    # Получение параметров запроса
    logs = driver.get_log('performance')
    target_url = '/messenger-v2/conversations?'
    for entry in logs:
        log = json.loads(entry['message'])['message']
        
        # Ищем событие отправки запроса
        if log['method'] == 'Network.requestWillBeSent':
            request_params = log['params']['request']
            url = request_params['url']
            
            # Фильтруем нужный URL (например, ваш API мессенджера)
            if target_url in url:
                # print(f"--- НАЙДЕНЫ ЗАГЛОВКИ ЗАПРОСА ДЛЯ: {url} ---")
                
                # Вот эти заголовки ТАКЖЕ содержат куки и токены, их можно использовать дальше!
                request_headers = request_params['headers']
    if not request_headers: 
        print(request_headers)

    driver.quit()

    return request_headers, session_cookies

def get_chats_to_load(
        request_headers,
        session_cookies
):
    next_cursor = None
    load_next = True
    # session_cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
    # dt_filter = dt(2026,9,20, tzinfo=timezone.utc)
    new_load_dt = dt.now()
    dt_filter = get_last_load_dt().replace(tzinfo=None)
    # save_dir = os.path.join(
    #     os.getcwd(),
    #     'export',
    #     'conversations'
    # )
    # os.makedirs(save_dir, exist_ok=True)

    while load_next:
        if not next_cursor:
            url = "https://kosher-track.com/messenger-v2/conversations?channel_id=2224&cc_id=27&keyset=1&limit=50&bucket=all"
        else:
            url = f"https://kosher-track.com/messenger-v2/conversations?channel_id=2224&cc_id=27&keyset=1&limit=50&bucket=all&cursor={next_cursor}"
        response = requests.get(url, headers=request_headers, cookies=session_cookies)
        # Сохранить 'data' из запроса
        # save_path = os.path.join(save_dir, str(dt.now()).replace(':', '')+'.json')
        # with open(save_path, 'w', encoding='utf-8') as f:
        #     f.write(json.dumps(response.json()['data'], indent=4, ensure_ascii=False))        
        # Проверить даты последних сообщений, применить остановку по фильтру
        uuids = []
        for conv in response.json()['data']:
            last_message_at = dt.fromisoformat(conv['last_message_at']).replace(tzinfo=None)
            uuids.append(conv['uuid'])
            if last_message_at < dt_filter:
                load_next = False
                add_chat_to_load(uuids)
                uuids = []
                break
        # 
        add_chat_to_load(uuids)
        # Сохранить next_cursor
        next_cursor = response.json()['next_cursor']
        random_sleep = random.uniform(5.1, 11.3)
        sleep(random_sleep)
    # 
    set_last_load_dt(new_load_dt)

def load_chats(
        request_headers,
        session_cookies
):
    uuids = get_chats_uuids()
    print('Скачиваю чаты')
    for i in tqdm(range(len(uuids))):
        # item = uuids[i]
        uuid = uuids.pop(0)
        # 
        # if item['checked']: continue
        # 
        # uuid = item['uuid']
        has_more = False
        before_id = None
        prev_messages = []
        # 
        while True:
            random_sleep = random.uniform(5.1, 11.3)
            sleep(random_sleep)
            # 
            url = f'https://kosher-track.com/messenger-v2/conversations/{uuid}'
            if has_more:
                url += f'?before_id={before_id}'
            # 
            response = requests.get(url, headers=request_headers, cookies=session_cookies)
            if response.json()['has_more']:
                prev_messages = response.json()['messages'] + prev_messages
                has_more = True
                before_id = response.json()['messages'][0]['id']
                # print('before_id', before_id)
                continue
            else:
                data = response.json()
                data['messages'] += prev_messages


            save_path = os.path.join(chats_dir, uuid+'.json')
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=4, ensure_ascii=False))
            parse_chat_to_db(save_path)
            break
        rewrite_chats_to_load(uuids)
        # 
        # uuids[i]['checked'] = True

        # save_path = os.path.join(os.getcwd(), 'load_chat_task.json')
        # with open(save_path, 'w', encoding='utf-8') as f:
        #     f.write(json.dumps(uuids, indent=4, ensure_ascii=False))

def main():
    request_headers, session_cookies = get_kosher_auth_data()
    get_chats_to_load(request_headers, session_cookies)
    load_chats(request_headers, session_cookies)
    # if dt.now().hour == 12: get_kosher_subs_events(request_headers, session_cookies)
    create_reports()
    send_reports_to_gdrive()

if __name__ == '__main__':
    main()
