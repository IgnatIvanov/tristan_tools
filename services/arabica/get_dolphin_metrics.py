import pandas as pd
# 
from services.arabica.database import get_engine

def get_dolphin_metrics() -> pd.DataFrame:
    #  Получение данных dolphin для построения отчётов
    engine = get_engine()
    df = pd.read_sql_table('dolphin_metrics', con=engine)
    _filter = ((df['spend'] != 0) | (df['clicks'] != 0) | (df['subs'] != 0) | (df['contacts'] != 0) | (df['regs'] != 0) | (df['purchase'] != 0))
    df = df[_filter]
    return df