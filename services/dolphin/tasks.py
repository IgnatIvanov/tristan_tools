import os
import json
from datetime import date
# 
plan_path = os.path.join('services', 'dolphin', 'update_plan.json')

def set_date_to_update(
        add_date: date
):
    # Сохранение даты для последующей выгрузки метрик
    # plan_path = os.path.join('services', 'dolphin', 'update_plan.json')
    if not os.path.exists(plan_path): 
        plan = []
    else:
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan = json.loads(f.read())
    plan.append(str(add_date))
    plan = list(set(plan))
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(plan, indent=4, ensure_ascii=False))

def get_dates_to_update() -> list:
    # Получение списка дат для обновления
    with open(plan_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())

def rewrite_dates_to_update(plan: list):
    # Перезапись списка дат для онбовления полностью
    # Пример сценарий из списка проверили одну дату, удалили и нужно переписать
    plan = list(set(plan))
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(plan, indent=4, ensure_ascii=False))