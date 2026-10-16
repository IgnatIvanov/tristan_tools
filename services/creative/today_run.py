import os
import sys
import json
import yt_dlp
# from gallery_dl import job, config
import asyncio
import psycopg2
import requests
from time import sleep
import pandas as pd
from datetime import datetime as dt, date, timedelta
# from pydantic import BaseModel, RootModel
from sqlalchemy import text
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile
# 
from services.arabica.database import get_db_credentials
from services.arabica.database import get_engine
from services.creative.access.get_token import get_access_token
from services.reports.creative_stats import create_creative_stats_report

BOT_TOKEN = get_access_token()
bot = Bot(token=BOT_TOKEN)
CHAT_ID = -5334213922  # ид группы куда отправлять сообщения

# ид переписки бота со мной
# CHAT_ID = 1605001845
# CHAT_ID = 8828714939

# Списки расширений для Telegram
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')

async def send_ad_video(
        chat_id: int, 
        media_path: str, 
        text_caption: str,
        stats_path: str|None = None
):
    # Указываем путь к локальному файлу через FSInputFile
    media_file = FSInputFile(media_path)   
    _, extension = os.path.splitext(media_path.lower()) 
    try:
        # 1. Отправляем креатив (видео или фото) с текстом
        if extension in ('.mp4', '.mov', '.avi', '.webm'):
            creo_msg = await bot.send_video(
                chat_id=chat_id,
                video=media_file,
                caption=text_caption,
                parse_mode="HTML"
            )
        else:
            creo_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=media_file,
                caption=text_caption,
                parse_mode="HTML"
            )
        print("Креатив с подписью успешно отправлен!")
        # print("Видео с подписью успешно отправлено!")
        if stats_path and os.path.exists(stats_path):
            excel_file = FSInputFile(stats_path)
            await bot.send_document(
                chat_id=chat_id,
                document=excel_file,
                caption="📊 Метрики качества для креатива выше",
                reply_to_message_id=creo_msg.message_id  # Связываем сообщения
            )
        print("Файл с метриками успешно отправлен!")
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {e}")
    finally:
        # Закрываем сессию бота (обязательно для aiogram 3.x в одиночных скриптах)
        await bot.session.close()
        os.remove(media_path)
        sleep(1)

    # if stats_path and os.path.exists(stats_path):
    #     excel_file = FSInputFile(stats_path)
    #     await bot.send_document(
    #         chat_id=chat_id,
    #         document=excel_file,
    #         caption="📊 Метрики качества для креатива выше",
    #         reply_to_message_id=creo_msg.message_id  # Связываем сообщения
    #     )


def flatten_dicts_iterative(nested_list):
    result = []
    # Копируем исходный список в стек, чтобы не менять оригинал
    stack = list(nested_list)
    
    while stack:
        current = stack.pop(0)  # Берем первый элемент
        if isinstance(current, dict):
            result.append(current)
        elif isinstance(current, (list, tuple)):
            # Добавляем элементы в начало стека, сохраняя порядок
            stack = list(current) + stack
            
    return result

def extract_creo_url(creo_dict: dict):
    if creo_dict == {}: return ''
    return creo_dict['instagram_permalink_url']

def download_media(
        url: str,
        art_name: str, 
        output_path=os.path.join('.', 'temp_creo_on_air'),
) -> str|None:
    # temp_dir = os.path.join('.', 'temp_creo_on_air')
    saved_file_path = None
    def my_hook(d):
        nonlocal saved_file_path
        if d['status'] == 'finished':
            # Перехватываем итоговое имя файла
            saved_file_path = d['filename']
    ydl_opts = {
        # 'outtmpl': f'{output_path}%(title)s.%(ext)s',
        'outtmpl': f'{os.path.join(output_path, art_name)}.%(ext)s',
        'quiet': True,
        'progress_hooks': [my_hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            if saved_file_path:
                print(f"Файл успешно сохранен по пути: {saved_file_path}")
                return saved_file_path
            else:
                print("Загрузка завершена, но путь к файлу определить не удалось.")
                return None
        except Exception as e:
            print(f"Ошибка при скачивании {url}: {e}")


def download_media_hybrid(
        url, 
        art_name: str, 
        output_path=os.path.join('.', 'temp_creo_on_air_2'),
):
    """
    Универсальный скачиватель: видео качает через yt-dlp, 
    а фото — вытягивает из метаданных yt-dlp и качает через requests.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 1. Сначала извлекаем метаданные (информацию о посте) БЕЗ скачивания самого файла
    ydl_opts_info = {
        'quiet': True,
        # 'proxy': proxy_url,
        'skip_download': True,  # Только парсим инфу
        'ignoreerrors': True,
        'ignore_no_formats_error': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            
        # Проверяем, что нам вернул yt-dlp
        if not info:
            print("Не удалось извлечь метаданные публикации.")
            return None

        # print('loaded_page_info')
        # print(info)
            
        # 2. Определяем, видео это или статичное фото
        # Если в метаданных есть прямые видео-форматы:
        if info.get('formats') or info.get('url') and info.get('ext') == 'mp4':
            print("Обнаружено видео. Запускаем скачивание через yt-dlp...")
            
            saved_file_path = None
            def hook(d):
                nonlocal saved_file_path
                if d['status'] == 'finished':
                    saved_file_path = d['filename']

            ydl_opts_download = {
                # 'outtmpl': f'{output_path}/%(title)s.%(ext)s',
                'outtmpl': f'{os.path.join(output_path, art_name)}.%(ext)s',
                'quiet': True,
                # 'proxy': proxy_url,
                'progress_hooks': [hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                ydl.download([url])
            return saved_file_path

        # 3. Если это фото (видео-форматов нет), забираем прямую ссылку на картинку из превью
        else:
            print("Обнаружено изображение. Скачиваем напрямую из CDN Meta...")
            # В info['thumbnail'] лежит прямая публичная ссылка на изображение в fbcdn.net
            img_url = info.get('thumbnail')
            if not img_url:
                print("Не удалось найти ссылку на изображение в метаданных.")
                return None
                
            # Генерируем имя файла на основе ID поста
            post_id = info.get('id', 'photo')
            file_name = f"instagram_{post_id}.jpg"
            full_path = os.path.join(output_path, file_name)
            
            # Скачиваем картинку через requests (из CDN Meta авторизация не нужна)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            # Используем тот же прокси для стабильности запроса к CDN
            # proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            
            # response = requests.get(img_url, headers=headers, proxies=proxies, stream=True)
            response = requests.get(img_url, headers=headers, stream=True)
            if response.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return full_path
            else:
                print(f"Ошибка скачивания картинки из CDN. Статус: {response.status_code}")
                return None

    except Exception as e:
        print(f"Ошибка при обработке ссылки {url}: {e}")
        return None


def today_on_air(
        start_date: date = date.today()
):
    """ Ежедневное получение креативов из выгруженной статистики по работающим рекламным объявлениям
        Запуск после выгрузки из Dolphin
    """    
    # создаём отчёты с метриками по каждому креативу
    creo_stats_dir = create_creative_stats_report()

    creds = get_db_credentials()
    conn = psycopg2.connect(
        dbname=creds['db_name'],
        user=creds['username'], 
        password=creds['password'], 
        host=creds['ip_addr'], 
        port="5432"
    )
    engine = get_engine()
    
    # * Получаем данные из Dolphin
    # start_date = date.today()
    # start_date = dt(2026,10,15).date()
    end_date = start_date + timedelta(days=1)
    # select_query = """
    #     select 
    #         creo_json,
    #         metrics_date,
    #         art_name
    #     from dolphin_metrics
    #     where created_at >= %s AND created_at < %s
    # """
    select_query = """
        SELECT 
            creo_json,
            metrics_date,
            art_name
        FROM dolphin_metrics
        WHERE created_at >= :start_dt AND created_at < :end_dt
    """
    # with conn.cursor() as cursor:
    #     cursor.execute(select_query, (start_date, end_date))
    #     result = cursor.fetchall()
    # result = flatten_dicts_iterative(result)
    df = pd.read_sql_query(
        sql=text(select_query),
        con=engine,
        params={'start_dt': start_date, 'end_dt': end_date}
    )
    df['metrics_date'] = pd.to_datetime(df['metrics_date']).dt.date
    df['creo_url'] = df['creo_json'].apply(extract_creo_url)
    # df['metrics_date'] = pd.to_datetime(df['metrics_date'])
    # result = df.to
    
    # print(result)
    # with open('result.json', 'w', encoding='utf-8') as f:
    #     # def json_serial(obj):
    #     #     if isinstance(obj, date):
    #     #         return obj.isoformat()
    #     #     raise TypeError(f"Type {type(obj)} not serializable")
    #     f.write(
    #         # json.dumps(result, indent=4, ensure_ascii=False)
    #         # json.dumps(result, default=json_serial, indent=4)
    #         # json.dumps(df.to_json(indent=4), indent=4)
    #         df.to_json(indent=4, orient='records')
    #     )
    
    # * Группируем по названию креатива
    #   Для каждого крео по названию получаем даты когда работал
    #   Выбираем одну ссылку для каждого крео по названию
    creo_send = {}
    # TODO: Обработка записей без указания крео или без параметров url
    for r in df.to_dict(orient='records'):
        creo_send.setdefault(
            r['art_name'], 
            {
                'dates': [],
                'url': ''
            }
        )
        item = creo_send[r['art_name']]
        item['url'] = r['creo_url']
        item['dates'].append(str(r['metrics_date']))
        creo_send[r['art_name']] = item
    for key, value in creo_send.items():
        value['dates'] = list(set(value['dates']))
        value['dates'] = sorted(value['dates'])
        creo_send[key] = value
    with open('result.json', 'w', encoding='utf-8') as f:
        f.write(
            json.dumps(creo_send, indent=4, ensure_ascii=False)
        )
    
    # * Проходим по каждому крео
    #   Скачиваем медиа, готовим текст сообщения, отправляем
    #   Удаляем загруженный файл
    for art_name, value in creo_send.items():
        if value['url'] == '': continue

        print('\n'*5)
        print('start processing url')
        print(value['url'])
        print(art_name)
        print()
        # media_path = download_media(
        #     art_name=art_name,
        #     url=value['url']
        # )

        # test
        media_path = download_media_hybrid(
            url=value['url'],
            art_name=art_name,
        )
        
        send_text = ''
        send_text += f'Крео: {art_name}\n'
        send_text += f'Даты пролива:\n'
        for d in value['dates']:
            send_text += f'- {str(d)}\n'
        
        if media_path is None:
            print("Не удалось скачать медиа для крео")
            print(send_text)
            continue

        # await send_ad_video(
        #     chat_id=CHAT_ID,
        #     file_path=media_path,
        #     text_caption=send_text,
        # )
        # task = asyncio.create_task(
        #     send_ad_video(
        #         chat_id=CHAT_ID,
        #         file_path=media_path,
        #         text_caption=send_text,
        #     )
        # )
        stats_path = os.path.join(creo_stats_dir, art_name+'.xlsx')
        asyncio.run(
            send_ad_video(
                chat_id=CHAT_ID,
                media_path=media_path,
                text_caption=send_text,
                stats_path=stats_path,
            )
        )

if __name__ == '__main__':
    today_on_air(
        start_date = dt(2026,10,14).date()
    )
