import pandas as pd
# 
from services.arabica.database import get_engine

def get_dolphin_metrics() -> pd.DataFrame:
    #  Получение данных dolphin для построения отчётов
    engine = get_engine()
    return pd.read_sql_table('dolphin_metrics', con=engine)