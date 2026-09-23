import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
# 
from scripts.dolphin_update_data import run_fb_accounts_update_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    
    # Настраиваем интервал в 4 часа
    # scheduler.add_job(run_fb_accounts_update_data, 'interval', hours=4)
    scheduler.add_job(
        run_fb_accounts_update_data, 
        'cron', 
        hour=11, 
        minute=0,
        id='dolphin_start_fb_sync'  # Полезно задать уникальный ID для логов
    )
    scheduler.start()
    
    logging.info("Фоновый планировщик запущен. Нажмите Ctrl+C для выхода.")
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Планировщик остановлен.")
