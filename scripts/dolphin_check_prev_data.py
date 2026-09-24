import os
import json
import requests
import pandas as pd
from time import sleep
from pathlib import Path
from datetime import datetime as dt, timedelta, date
# 
from services.dolphin.settings import Settings
from services.dolphin.stats import get_stats_on_date
from services.dolphin.tasks import set_date_to_update
from services.dolphin.tasks import get_dates_to_update

from services.arabica.database import get_engine
# 
settings = Settings()

def date_backwards_generator(
        start_date: date, 
        end_date: date
):
    current_date = start_date
    while current_date >= end_date:
        yield current_date
        current_date -= timedelta(days=1)

def check_prev_dates_spend() -> list:
    # Посуточно проверяем траты и если трат стало за сутки больше, 
    # то сохраняем дату для последующей выгрузки объявлений

    # Получить из ara ежедневные траты
    engine = get_engine()
    query = '''
        select
            metrics_date,
            sum(spend) as spend
        from dolphin_metrics
        group by metrics_date
        order by metrics_date
    '''
    df = pd.read_sql(query, con=engine)
    # делаем словарь формата {metrics_date: spend}
    spend_dict = df.set_index('metrics_date')['spend'].to_dict()
    # 
    # Проверка трат по датам
    today = dt.now().date()
    past_limit = dt(2026, 7, 24).date()  ## Раньше этой даты метрик не было
    for date in date_backwards_generator(today, past_limit):
        spend_dict.setdefault(date, 0)
        ara_spend = round(spend_dict[date], 2)
        dolphin_spend = get_stats_on_date(
            target_date=date, 
            aggregate_columns=['spend']
        )['data']['spend']
        dolphin_spend = round(dolphin_spend, 2)        
        if ara_spend < dolphin_spend:
            diff = abs(ara_spend - dolphin_spend)
            if diff < 10: continue
            set_date_to_update(date)
    return get_dates_to_update()



if __name__ == '__main__':
    check_prev_dates_spend()
