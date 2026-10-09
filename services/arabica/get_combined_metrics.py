import pandas as pd
from services.arabica.database import get_engine

def get_combined_metrics():
    # Получение объединённых метрик: dolphin + ara + kosher
    # Метрики объединены по дате и id из facebook
    # Показывает конверсии по тратам на рекламу
    engine = get_engine()
    df = pd.read_sql('v_fbspend_and_kosher', con=engine)
    return df

def get_combined_metrics_by_date():
    # Получение объединённых метрик: dolphin + ara + kosher
    # Метрики объединяются только по дате
    engine = get_engine()
    df = pd.read_sql('v_fbspend_and_kosher_by_date', con=engine)
    return df

def get_combined_metrics_dima() -> pd.DataFrame:
    # Получение объединённых метрик: dolphin + kosher
    # для отчётов Димы
    # Метрики объединяются только по дате
    engine = get_engine()
    df = pd.read_sql('v_dima_dolphin_kosher_combined', con=engine)
    df.fillna(
        inplace=True,
        value={
            'cam_id': 'Нет объявления',
            'adset_id': 'Нет объявления',
            'ad_id': 'Нет объявления',
            'art_name': 'Нет объявления',
            'tier': 'Нет объявления',
            'buyer_name': 'Нет объявления',
            'impressions': 0,
            'spend': 0,
            'click': 0,
            'sub_count': 0,
            'dialog_count': 0,
            'ftd_count': 0,
        }
    )
    return df