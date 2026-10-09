import pandas as pd
from services.arabica.database import get_engine

def set_to_update():
    # просмотр чатов и постановка на создание ии отчёта
    # устанавливаем признак need_analisis = true
    engine = get_engine()
    df = pd.read_sql('kosher_chat', con=engine)