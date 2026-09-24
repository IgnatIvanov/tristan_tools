import requests
from datetime import date
# 
from services.dolphin.settings import Settings
from services.dolphin.access.get_token import get_access_token
# 
settings = Settings()

def get_stats_on_date(
        target_date: date, 
        aggregate_columns: list[str],
):
    # Получение метрик за день из Дельфина
    api_token = get_access_token()
    url = f'https://{settings.BASE_URL}/api/v1/fb-ads/total-stats'
    headers = {
        'Authorization': f'Bearer {api_token}',
        # 'Content-Type': 'application/json'
    }
    params = {
        'perPage': 100,
        'page': 1,
        'from_date': str(target_date),
        'to_date': str(target_date),
        'currency': 'USD',
        'aggregateColumns[]': aggregate_columns,
        'showArchivedAds': 1,
        'with_trashed': 1,
        'showArchivedAdAccount': 1,
        'showArchivedAdsets': 1
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()