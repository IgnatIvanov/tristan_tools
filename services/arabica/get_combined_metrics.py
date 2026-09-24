import pandas as pd
from services.arabica.database import get_engine

def get_combined_metrics():
    # Получение объединённых метрик: dolphin + ara + kosher
    engine = get_engine()
    df = pd.read_sql('v_fbspend_and_kosher', con=engine)
    return df
