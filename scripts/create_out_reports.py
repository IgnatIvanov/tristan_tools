import os
import pandas as pd
import numpy as np
from datetime import date
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
# 
from services.arabica.get_dolphin_metrics import get_dolphin_metrics
from services.reports.dima_reports_20260920 import main as create_dima_report_20260920
from services.reports.nikita_total_report_1 import prepare_report as create_nikita_total_report_1

def get_total_report(
        df: pd.DataFrame,
        start_date: date,
        end_date: date,
) -> pd.DataFrame:
    """Общий отчёт по конверсиям 

    Args:
        df (pd.DataFrame): метрики
        start_date (date): _description_
        end_date (date): _description_

    Returns:
        pd.DataFrame: _description_
    """    
    _filter = ((df['metrics_date']>=start_date) & (df['metrics_date']<=end_date))
    df = df[_filter]
    total_report = df.groupby('art_name', as_index=False).agg({
        'spend': 'sum',
        'clicks': 'sum',
        'subs': 'sum',
        'contacts': 'sum',
        'regs': 'sum',
        'purchase': 'sum',
    })
    total_report['click_cost'] = (total_report['spend'] / total_report['clicks']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['sub_cost'] = (total_report['spend'] / total_report['subs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['contact_cost'] = (total_report['spend'] / total_report['contacts']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['reg_cost'] = (total_report['spend'] / total_report['regs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['purchase_cost'] = (total_report['spend'] / total_report['purchase']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)

    total_report['spend'] = total_report['spend'].round(2)

    total_report = total_report[[
        'art_name', 'spend',
        'clicks', 'click_cost',
        'subs', 'sub_cost',
        'contacts', 'contact_cost',
        'regs', 'reg_cost',
        'purchase', 'purchase_cost'
    ]]
    return total_report

def get_report_total_by_tier(
        df: pd.DataFrame,
        start_date: date,
        end_date: date,
) -> pd.DataFrame:
    """Отчёт по конверсиям с разбивкой по регионам (tier)

    Args:
        df (pd.DataFrame): _description_
        start_date (date): _description_
        end_date (date): _description_

    Returns:
        pd.DataFrame: _description_
    """    
    # 1. Фильтрация по датам
    _filter = ((df['metrics_date'] >= start_date) & (df['metrics_date'] <= end_date))
    df = df[_filter].copy()
    
    # 2. Строим сводную таблицу (в columns добавляем 'geo')
    total_report = df.pivot_table(
        index='art_name',
        columns='tier', 
        values=['spend', 'clicks', 'subs', 'contacts', 'regs', 'purchase'],
        aggfunc='sum',
        fill_value=0
    )
    
    # Получаем уникальные ГЕО, которые есть в данных
    geos = total_report.columns.get_level_values(1).unique()
    
    # 3. Расчет стоимостей для каждого ГЕО
    for geo in geos:
        total_report[('click_cost', geo)] = total_report[('spend', geo)] / total_report[('clicks', geo)]
        total_report[('sub_cost', geo)] = total_report[('spend', geo)] / total_report[('subs', geo)]
        total_report[('contact_cost', geo)] = total_report[('spend', geo)] / total_report[('contacts', geo)]
        total_report[('reg_cost', geo)] = total_report[('spend', geo)] / total_report[('regs', geo)]
        total_report[('purchase_cost', geo)] = total_report[('spend', geo)] / total_report[('purchase', geo)]
        
        # Округляем spend
        total_report[('spend', geo)] = total_report[('spend', geo)].round(2)

    # Очищаем расчетные стоимости от inf и NaN
    total_report = total_report.replace([np.inf, -np.inf], np.nan).fillna(0).round(2)
    
    # 4. МЕНЯЕМ УРОВНИ МЕСТАМИ, чтобы ГЕО стало главным (верхним) уровнем
    total_report = total_report.swaplevel(0, 1, axis=1)
    
    # 5. Задаем строгий желаемый порядок метрик внутри каждого ГЕО
    metric_order = [
        'spend', 'clicks', 'click_cost', 'subs', 'sub_cost', 
        'contacts', 'contact_cost', 'regs', 'reg_cost', 'purchase', 'purchase_cost'
    ]
    
    # Создаем идеальный шаблон шапки: сначала ГЕО, внутри него метрики по нашему списку
    correct_columns = pd.MultiIndex.from_product([geos, metric_order])
    
    # Безопасно перестраиваем таблицу по новому шаблону
    total_report = total_report.reindex(columns=correct_columns, fill_value=0)
    
    # 6. Сбрасываем индекс, чтобы art_name стал обычной колонкой
    total_report = total_report.reset_index()
    
    return total_report

def get_report_total_by_url(
        df: pd.DataFrame,
        start_date: date,
        end_date: date,
) -> pd.DataFrame:
    """Отчёт по конверсиям с по url (tier)

    Args:
        df (pd.DataFrame): _description_
        start_date (date): _description_
        end_date (date): _description_

    Returns:
        pd.DataFrame: _description_
    """     
    _filter = ((df['metrics_date']>=start_date) & (df['metrics_date']<=end_date))
    df = df[_filter]
    total_report = df.groupby('link', as_index=False).agg({
        'spend': 'sum',
        'clicks': 'sum',
        'subs': 'sum',
        'contacts': 'sum',
        'regs': 'sum',
        'purchase': 'sum',
    })
    total_report['click_cost'] = (total_report['spend'] / total_report['clicks']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['sub_cost'] = (total_report['spend'] / total_report['subs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['contact_cost'] = (total_report['spend'] / total_report['contacts']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['reg_cost'] = (total_report['spend'] / total_report['regs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['purchase_cost'] = (total_report['spend'] / total_report['purchase']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)

    total_report['spend'] = total_report['spend'].round(2)

    total_report = total_report[[
        'link', 'spend',
        'clicks', 'click_cost',
        'subs', 'sub_cost',
        'contacts', 'contact_cost',
        'regs', 'reg_cost',
        'purchase', 'purchase_cost'
    ]]
    return total_report

def get_total_report_by_date(
        df: pd.DataFrame,
        start_date: date,
        end_date: date,
) -> pd.DataFrame:
    """Общий отчёт по конверсиям 

    Args:
        df (pd.DataFrame): метрики
        start_date (date): _description_
        end_date (date): _description_

    Returns:
        pd.DataFrame: _description_
    """    
    _filter = ((df['metrics_date']>=start_date) & (df['metrics_date']<=end_date))
    df = df[_filter]
    total_report = df.groupby('metrics_date', as_index=False).agg({
        'spend': 'sum',
        'clicks': 'sum',
        'subs': 'sum',
        'contacts': 'sum',
        'regs': 'sum',
        'purchase': 'sum',
    })
    # 
    # 2. Добавление строки общего итога
    numeric_cols = ["spend", "clicks", "subs", "contacts", "regs", "purchase"]
    total_values = total_report[numeric_cols].sum()
    # 
    # 3. Прикрепляем строку к основному DataFrame
    total_row = {"metrics_date": "Total"}
    for col in numeric_cols:
        total_row[col] = total_values[col]
    total_report = pd.concat(
        [total_report, pd.DataFrame([total_row])], ignore_index=True
    )
    # 
    # 
    total_report['click_cost'] = (total_report['spend'] / total_report['clicks']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['sub_cost'] = (total_report['spend'] / total_report['subs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['contact_cost'] = (total_report['spend'] / total_report['contacts']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['reg_cost'] = (total_report['spend'] / total_report['regs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['purchase_cost'] = (total_report['spend'] / total_report['purchase']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)

    total_report['spend'] = total_report['spend'].round(2)

    total_report = total_report[[
        'metrics_date', 'spend',
        'clicks', 'click_cost',
        'subs', 'sub_cost',
        'contacts', 'contact_cost',
        'regs', 'reg_cost',
        'purchase', 'purchase_cost'
    ]]
    return total_report

def main(
        # metrics_path: str = 'metrics.csv',
):
    """Построение отчётов на основании метрик

    Args:
        metrics_path (str, optional): _description_. Defaults to 'metrics.csv'.
    """    
    # Чтение файла с метриками
    # df = pd.read_csv(metrics_path, dtype=str)
    df = get_dolphin_metrics()
    # 
    cols_to_convert = ['spend', 'clicks', 'subs', 'contacts', 'regs', 'purchase']
    for col in cols_to_convert:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # 
    _filter = ((df['spend'] != 0) | (df['clicks'] != 0) | (df['subs'] != 0) | (df['contacts'] != 0) | (df['regs'] != 0) | (df['purchase'] != 0))
    df = df[_filter]
    # 
    # dest_path = os.path.join('.', 'google_drive_out', 'dolphin_1')
    dest_path = os.path.join('documents_out', 'google_drive_out', 'dolphin_1')
    os.makedirs(dest_path, exist_ok=True)
    # 
    xlsx_path = os.path.join(dest_path, 'metrics.xlsx')
    df.to_excel(xlsx_path, index=False)
    # 
    # df['metrics_date'] = df['metrics_date'].apply(lambda x: dt.fromisoformat(x).date())
    df['metrics_date'] = df['metrics_date'].apply(lambda x: x.date())
    # 
    # Определяем периоды для создания ежемесячных отчётов
    # На основании дат из метрик
    dt_min = df['metrics_date'].min()
    dt_min = dt(dt_min.year, dt_min.month, 1).date()
    dt_max = df['metrics_date'].max() + relativedelta(months=1)
    # 
    dt_start = dt_min
    dt_end = dt_min + relativedelta(months=1)
    periods = []  # Тут будут помесячные интервалы, для каждого месяца первая и последняя дата
    while dt_end <= dt_max:
        period = {
            'start': dt_start, 
            'end': dt_end - relativedelta(days=1),
        }
        periods.append(period)
        dt_start += relativedelta(months=1)
        dt_end += relativedelta(months=1)
    # 
    # Построение ежемесячных отчётов по метрикам
    for p in periods:
        total_report = get_total_report(df, p['start'], p['end'])
        save_path = os.path.join(dest_path, 'reports', 'total')
        os.makedirs(save_path, exist_ok=True)
        save_name = str(p['start']) + '.xlsx'
        total_report.to_excel(os.path.join(save_path, save_name), index=False)
        # 
        # 
        total_by_tier = get_report_total_by_tier(df, p['start'], p['end'])
        save_path = os.path.join(dest_path, 'reports', 'total_by_tier')
        os.makedirs(save_path, exist_ok=True)
        save_name = str(p['start']) + '.xlsx'
        total_by_tier.to_excel(os.path.join(save_path, save_name))
        # 
        # 
        total_by_tier = get_report_total_by_url(df, p['start'], p['end'])
        save_path = os.path.join(dest_path, 'reports', 'total_by_url')
        os.makedirs(save_path, exist_ok=True)
        save_name = str(p['start']) + '.xlsx'
        total_by_tier.to_excel(os.path.join(save_path, save_name))
        # 
        # 
    total_by_date = get_total_report_by_date(df, dt_min, dt_max)
    save_path = os.path.join(dest_path)
    os.makedirs(save_path, exist_ok=True)
    # save_name = str(p['start']) + '.xlsx'
    save_name = 'Общее по дням.xlsx'
    total_by_date.to_excel(os.path.join(save_path, save_name))

    # Создание отдельных отчётов
    create_dima_report_20260920()
    create_nikita_total_report_1()

if __name__ == '__main__':
    main()
