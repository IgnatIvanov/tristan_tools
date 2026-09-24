import os
import requests
from time import sleep
from datetime import date, datetime as dt
# 
from services.dolphin.settings import Settings
from services.dolphin.access.get_token import get_access_token
from services.arabica.save import save_dolphin_metrics_to_ara as save_metrics
from services.arabica.extract_fields import *
from services.dolphin.tasks import *
# 
settings = Settings()
# 

def load_ads(
            # self,
            _date: date,
            # save_path: str,
    ):
        # _path = os.path.join(save_path, str(_date)+'.csv')
        # if os.path.exists(_path): os.remove(_path)
        api_token = get_access_token()
        
        url = f'https://{settings.BASE_URL}/api/v1/fb-ads'        
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        }    
        params = {
            'perPage': 100,  # Запрашиваем по 100 объявлений за раз (максимум)
            'page': 1,
            'from_date': _date,
            'to_date': _date,
            'currency': 'USD',

            # Включаем все возможные архивы и удаленку на всех уровнях
            'with_trashed': 1,  
            'showArchivedAds': 1,
            'showArchivedAdsets': 1,
            'showArchivedAdAccount': 1,
            'showAccountArchivedAdAccount': 1,

            # Обязательно запрашиваем таргет адсета (там лежит ГЕО)
            'aggregateColumns[]': [
                'adset_targeting',  # Вытащить настройки таргетинга (ГЕО)
                'spend',            # Расход
                'impressions',      # Показы
                'link_click',        # Клики
                'subscribe_total',
                'contact_total',
                'fb_pixel_complete_registration',
                'fb_pixel_purchase',
            ]
        }
        has_more_pages = True
        while has_more_pages:
            print(str(params['page']), end='_', flush=True)
            ads = []
            # 
            response = requests.get(url, headers=headers, params=params)
            # 
            if response.status_code != 200:
                print(f"❌ Ошибка API: {response.status_code}")
                print(response.text)
                print(response.url)
                sleep(60)
                # continue

            res_data = response.json()
            ads_list = res_data.get('data', [])
            if not ads_list:
                break

            for ad in ads_list:
                ad_id = ad.get('id')
                ad_name = ad.get('name')
                adset = ad.get('adset')
                adset_id = adset.get('adset_id')
                adset_name = adset.get('name')
                cam = adset['campaign']
                cam_id = cam.get('campaign_id')
                cam_name = cam.get('name')
                cab = cam.get('cab')
                cab_id = cab.get('id')
                cab_name = cab.get('name')
                # bm = cab.get('business')
                # bm_id = bm.get('id')
                # bm_id = bm.get('name')
                targeting = adset.get('targeting')
                countries = targeting.get('included_countries')
                geo_targeting = tuple([el['country_code'] for el in countries])
                art_name = get_art_name(ad_name)
                tier = get_tier(ad_name)
                #                 
                stats = ad.get('stats')
                impressions = stats.get('impressions')
                spend = stats.get('spend')
                clicks = stats.get('link_click')
                # leads = stats.get('fb_pixel_lead')
                subs = stats.get('subscribe_total')
                contacts = stats.get('contact_total')
                regs = stats.get('fb_pixel_complete_registration')
                purchase = stats.get('fb_pixel_purchase')
                # 
                creative = ad.get('creative')
                if creative is not None:
                    spec = creative.get('object_story_spec')
                    url_params = creative.get('url_tags')
                    if spec is not None:
                        link = spec.get('link')
                        if link is None: link = ''
                    else: link = 'object_story_spec is None'
                else: link = 'creative is None'
                # link = .get('object_story_spec').get('link')
                # 
                ads.append({
                    'metrics_date': _date,
                    'ad_id': ad_id,
                    'ad_name': ad_name,
                    'adset_id': adset_id,
                    'adset_name': adset_name,
                    'cam_id': cam_id,
                    'cam_name': cam_name,
                    'cab_id': cab_id,
                    'cab_name': cab_name,
                    'geo_targeting': geo_targeting,
                    'art_name': art_name,
                    'tier': tier,
                    'impressions': impressions,
                    'spend': spend,
                    'clicks': clicks,
                    'subs': subs,
                    'contacts': contacts,
                    'regs': regs,
                    'purchase': purchase,
                    'link': link,
                    'url_params': url_params,
                })
                # save_metrics()

            # save_metrics(
            #     metrics_date=_date,
            #     ads=ads,
            #     save_path=save_path,
            # )
            save_metrics(ads)
            

            sleep(3)

            if len(ads_list) < params['perPage']:
                has_more_pages = False
            else:
                params['page'] += 1

def main(dates_to_update: list[str]):
    # dates_to_update = get_dates_to_update()
    if len(dates_to_update) == 0: 
        print('No dates to update')
    else:
        while True:
            d = dates_to_update.pop(0)
            if type(d) == str: d = dt.fromisoformat(d).date()
            load_ads(d)
            rewrite_dates_to_update(dates_to_update)
            if len(dates_to_update) == 0: break



if __name__ == '__main__':
    dates_to_update = get_dates_to_update()
    main(dates_to_update)
