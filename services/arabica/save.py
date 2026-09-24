import psycopg2
import pandas as pd
from datetime import datetime as dt
# 
from services.arabica.database import get_db_credentials

def save_dolphin_metrics_to_ara(ads: list[dict]):
    # Сохранение метрик в БД arabica
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
        INSERT INTO dolphin_metrics (metrics_date, ad_id, ad_name, adset_id, adset_name, cam_id,
        cam_name, cab_id, cab_name, geo_targeting, art_name, tier,
        impressions, spend, clicks, subs, contacts, regs,
        purchase, link, url_params, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (metrics_date, cam_id, adset_id, ad_id) 
        DO UPDATE SET 
            ad_name = EXCLUDED.ad_name,
            adset_name = EXCLUDED.adset_name,
            cam_name = EXCLUDED.cam_name,
            cab_id = EXCLUDED.cab_id,
            cab_name = EXCLUDED.cab_name,
            geo_targeting = EXCLUDED.geo_targeting,
            art_name = EXCLUDED.art_name,
            tier = EXCLUDED.tier,
            impressions = EXCLUDED.impressions,
            spend = EXCLUDED.spend,
            clicks = EXCLUDED.clicks,
            subs = EXCLUDED.subs,
            contacts = EXCLUDED.contacts,
            regs = EXCLUDED.regs,
            purchase = EXCLUDED.purchase,
            link = EXCLUDED.link,
            created_at = EXCLUDED.created_at;
    """
    df = pd.DataFrame(ads)
    df['created_at'] = dt.now()
    df = df[['metrics_date', 'ad_id', 'ad_name', 'adset_id', 'adset_name', 'cam_id',
        'cam_name', 'cab_id', 'cab_name', 'geo_targeting', 'art_name', 'tier',
        'impressions', 'spend', 'clicks', 'subs', 'contacts', 'regs',
        'purchase', 'link', 'url_params', 'created_at']]
    df['geo_targeting'] = df['geo_targeting'].astype(str)    
    _filter = ((df['spend'] != 0) | (df['clicks'] != 0) | (df['subs'] != 0) | (df['contacts'] != 0) | (df['regs'] != 0) | (df['purchase'] != 0))
    df = df[_filter]
    try:
        records_to_insert = [tuple(x) for x in df.replace({pd.NA: None, float('nan'): None}).to_numpy()]
        cursor.executemany(insert_query, records_to_insert)
        conn.commit()
        # print(f"Успешно обработано строк: {len(df)}")

    except Exception as error:
        print(f"Ошибка при работе с PostgreSQL: {error}")
        print(*records_to_insert, sep='\n')
        conn.rollback()
    
    finally:
        # 6. Закрытие курсора и соединения
        cursor.close()
        conn.close()