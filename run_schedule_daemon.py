import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
# 
from scripts.dolphin_accounts_sync import run_dolphin_accounts_fb_sync
from scripts.dolphin_load_new_metrics import dolphin_load_new_metrics
from scripts.kosher_load_data import main as get_new_kosher_data
from services.kosher.get_events import main as get_kosher_subs_events
from services.creative.today_run import today_on_air

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    
    # Настраиваем интервал в 4 часа
    # scheduler.add_job(run_fb_accounts_update_data, 'interval', hours=4)
    scheduler.add_job(
        run_dolphin_accounts_fb_sync, 
        'cron', 
        hour=11, 
        minute=0,
        id='dolphin_start_fb_sync'  # Полезно задать уникальный ID для логов
    )
    scheduler.add_job(
        dolphin_load_new_metrics, 
        'cron', 
        hour=12, 
        minute=0,
        id='dolphin_load_new_metrics'
    )
    # Обновляем данные с кошера каждые 4 часа, выгрузка чатов
    scheduler.add_job(
        get_new_kosher_data,
        'cron', 
        hour='*/4', 
        minute=0,
        id='get_new_kosher_data'
    )
    # выгрузка событий подписки и отписки с кошера
    scheduler.add_job(
        get_kosher_subs_events,
        'cron', 
        hour=11, 
        minute=0,
        id='get_kosher_subs_events'
    )
    # Выгрузка крео в работе и отправка отчётов в тг
    scheduler.add_job(
        today_on_air, 
        'cron', 
        hour=13, 
        minute=0,
        id='today_on_air'
    )
    scheduler.start()
    
    logging.info("Фоновый планировщик запущен. Нажмите Ctrl+C для выхода.")
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Планировщик остановлен.")
