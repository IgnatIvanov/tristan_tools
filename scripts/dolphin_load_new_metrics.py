from scripts.dolphin_check_prev_data import check_prev_dates_spend
from services.dolphin.load_ads import main as load_new_ads_metrics
from scripts.create_out_reports import main as create_reports

def dolphin_load_new_metrics():
    # Загрузка и обновление новых метрик
    # 
    dates_to_load = check_prev_dates_spend()
    load_new_ads_metrics(dates_to_load)
    create_reports()
