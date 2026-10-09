import os
import json
from datetime import datetime as dt

load_list_path = os.path.join('services', 'kosher', 'chats_to_load.json')
last_load_path = os.path.join('services', 'kosher', 'last_load_date.txt')

def add_chat_to_load(uuids: list[str]):
    # Сохранение даты для последующей выгрузки метрик
    # plan_path = os.path.join('services', 'dolphin', 'update_plan.json')
    # print('сохраняю')
    if not os.path.exists(load_list_path): 
        load_list = []
    else:
        with open(load_list_path, 'r', encoding='utf-8') as f:
            load_list = json.loads(f.read())
    load_list += uuids
    load_list = list(set(load_list))
    with open(load_list_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(load_list, indent=4, ensure_ascii=False))

def get_chats_to_load() -> list:
    if not os.path.exists(load_list_path): 
        return []
    else:
        with open(load_list_path, 'r', encoding='utf-8') as f:
            return json.loads(f.read())

def rewrite_chats_to_load(chats_list: list):
    # Перезапись списка дат для онбовления полностью
    # Пример сценарий из списка проверили одну дату, удалили и нужно переписать
    chats_list = list(set(chats_list))
    with open(load_list_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(chats_list, indent=4, ensure_ascii=False))

def get_last_load_dt():
    if not os.path.exists(last_load_path):
        return dt(2026,7,24)
    with open(last_load_path, 'r', encoding='utf-8') as f:
        _dt = dt.fromisoformat(f.read()).replace(tzinfo=None)
        # _dt = dt(_dt.year, _dt.month, _dt.day)
        return _dt

def set_last_load_dt(_dt: dt):
    with open(last_load_path, 'w', encoding='utf-8') as f:
        f.write(_dt.isoformat())
