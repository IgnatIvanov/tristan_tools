import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
# 
from scripts.dolphin_accounts_sync import run_dolphin_accounts_fb_sync
from scripts.dolphin_load_new_metrics import dolphin_load_new_metrics

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
    scheduler.start()
    
    logging.info("Фоновый планировщик запущен. Нажмите Ctrl+C для выхода.")
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Планировщик остановлен.")
