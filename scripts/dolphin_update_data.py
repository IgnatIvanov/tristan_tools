import os
import json
import requests
from time import sleep
from pathlib import Path
# 
from services.dolphin.settings import Settings
from services.dolphin.access.get_token import get_access_token
# 
settings = Settings()

def run_fb_accounts_update_data():
    api_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
    # payload = ''
    params = {
        'perPage': 100,
        'page': 1,
        # 'from_date': '2026-09-20',
        # 'to_date': '2026-09-22',
        'currency': 'USD',
        # Передаем массив колонок, которые нужно сагрегировать
        # 'aggregateColumns[]': [
        #     'adset_targeting',
        #     'impressions',
        #     'link_click',
        #     'link_click_cpa',
        #     'cpm',
        #     'spend',
        #     'link_click_cr',
        #     'fb_mobile_add_payment_info'
        # ],
        'showArchivedAds': 0,
        'with_trashed': 1,
        # 'accountStatus[]': 'ACTIVE',
        'showArchivedAdAccount': 0,
        'showArchivedAdsets': 0
    }
    url = f'https://{settings.BASE_URL}/api/v1/fb-accounts'
    response = requests.get(url, headers=headers, params=params)
    data = json.loads(response.text)
    with open('responce.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    data = response.json()
    acc_ids = []
    acc_ids += [el['account'] for el in data['data']]
    n_pages = data['meta']['last_page']
    for i in range(n_pages):
        sleep(3)
        cur_page = i + 1
        if cur_page == 1: continue
        params['page'] = cur_page
        response = requests.get(url, headers=headers, params=params)
        acc_ids += [el['account'] for el in response.json()['data']]
    # 
    url = f'https://{settings.BASE_URL}/api/v1/fb-accounts/sync'
    payload = json.dumps({
        # "accountsIds": [
        #     "{{account_id}}"
        # ]
        "accountsIds": acc_ids
    })
    response = requests.request("POST", url, headers=headers, data=payload)
    # data = json.loads(response.text)
    # with open('responce.json', 'w', encoding='utf-8') as f:
    #     f.write(json.dumps(data, indent=4, ensure_ascii=False))



if __name__ == '__main__':
    run_fb_accounts_update_data()
    
