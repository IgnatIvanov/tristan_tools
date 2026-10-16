import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from services.arabica.get_combined_metrics import get_combined_metrics_dima

def get_total_report_by_date(
        df: pd.DataFrame,
        # start_date: date,
        # end_date: date,
        group_by_cols : list
) -> pd.DataFrame:
    """Общий отчёт по конверсиям 

    Args:
        df (pd.DataFrame): метрики

    Returns:
        pd.DataFrame: _description_
    """    
    
    # _filter = ((df['metrics_date']>=start_date) & (df['metrics_date']<=end_date))
    # df = df[_filter]
    # total_report = df.groupby('metrics_date', as_index=False).agg({
    total_report = df.groupby(group_by_cols, as_index=False).agg({
        'spend': 'sum',
        # 'clicks': 'sum',
        'subs': 'sum',
        'contacts': 'sum',
        # 'regs': 'sum',
        'purchase': 'sum',
    })
    # total_report['click_cost'] = (total_report['spend'] / total_report['clicks']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    total_report['sub_cost'] = (total_report['spend'] / total_report['subs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['contact_cost'] = (total_report['spend'] / total_report['contacts']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    # total_report['reg_cost'] = (total_report['spend'] / total_report['regs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    total_report['purchase_cost'] = (total_report['spend'] / total_report['purchase']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)

    total_report['spend'] = total_report['spend'].round(2)

    total_report = total_report[[
        # 'metrics_date', 
        *group_by_cols,
        'spend',
        # 'clicks', 'click_cost',
        'subs', 'sub_cost',
        'contacts', 'contact_cost',
        # 'regs', 'reg_cost',
        'purchase', 'purchase_cost'
    ]]
    total_report = total_report.sort_values(by=group_by_cols, ascending=False)

    # 4. Расчет строки ИТОГО
    # Суммируем только складываемые базовые метрики по всему датафрейму
    total_spend = total_report['spend'].sum()
    total_subs = total_report['subs'].sum()
    total_contacts = total_report['contacts'].sum()
    total_purchase = total_report['purchase'].sum()

    # Считаем производные метрики глобально для всей таблицы
    total_sub_cost = round(total_spend / total_subs, 2) if total_subs > 0 else 0.0
    total_contact_cost = round(total_spend / total_contacts, 2) if total_contacts > 0 else 0.0
    total_purchase_cost = round(total_spend / total_purchase, 2) if total_purchase > 0 else 0.0

    # Создаем словарь для строки итогов
    summary_row = {}
    
    # В первую колонку группировки пишем "Итого", остальные оставляем пустыми
    for i, col in enumerate(group_by_cols):
        summary_row[col] = "Итого" if i == 0 else ""
        
    # Заполняем просчитанные финальные метрики
    summary_row.update({
        'spend': round(total_spend, 2),
        'subs': total_subs,
        'sub_cost': total_sub_cost,
        'contacts': total_contacts,
        'contact_cost': total_contact_cost,
        'purchase': total_purchase,
        'purchase_cost': total_purchase_cost
    })

    # Превращаем строку в DataFrame и объединяем с основным отчетом
    summary_df = pd.DataFrame([summary_row])
    total_report = pd.concat([total_report, summary_df], ignore_index=True)


    return total_report


def create_excel_file():
    pass


def create_creative_stats_report() -> str:
    """Отчет с метриками по креативам
        По представлению данных из отчётов для Димы
        название крео+спенд+метрики
        общее по всем гео
        TODO: добавить разделение по гео
    """    
    save_dir = os.path.join('documents_out', 'google_drive_out', 'dolphin_1', 'Creo Stats')
    os.makedirs(save_dir, exist_ok=True)
    df = get_combined_metrics_dima()
    df.rename(
        inplace=True,
        columns={
            'sub_count': 'subs',
            'dialog_count': 'contacts',
            'ftd_count': 'purchase',
            'buyer_name': 'buyer',
        }
    )
    df['metrics_date'] = pd.to_datetime(df['metrics_date']).dt.date
    # print('columns', df.columns)
    # columns Index(['metrics_date', 'cam_id', 'adset_id', 'ad_id', 'art_name', 'tier',
    #    'buyer_name', 'impressions', 'spend', 'clicks', 'sub_count',
    #    'dialog_count', 'ftd_count'],
    #   dtype='str')

    # total_date_report = get_total_report_by_date(
    #     df=df,
    #     group_by_cols=group_by_cols
    # )

    creo_list = list(df['art_name'].unique())
    creo_list = sorted(creo_list)
    bar_format = '{n_fmt}/{total_fmt} |{bar:20}| {percentage:3.0f}% [{elapsed}<{remaining}] {postfix}'
    pbar = tqdm(creo_list, bar_format=bar_format)
    for c in pbar:
        pbar.set_postfix_str(f"Текущий: {str(c).ljust(25)}")
        creo_df = df[df['art_name'] == c]
        # creo_df = total_date_report[total_date_report['art_name'] == c]
        group_by_cols=[
            'metrics_date',
        ]
        creo_df.drop(
            inplace=True,
            columns=['art_name'],
        )
        creo_df = get_total_report_by_date(
            df=creo_df,
            group_by_cols=group_by_cols
        )
        # creo_df.sort_values(
        #     inplace=True,
        #     by=['metrics_date']
        # )
        save_path = os.path.join(
            save_dir,
            c+'.xlsx'
        )
        # creo_df.to_excel(save_path)
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            creo_df.to_excel(writer, index=False)
            worksheet = writer.sheets['Sheet1'] # По умолчанию pandas называет лист 'Sheet1'
            # Перебираем все столбцы и автоподбираем ширину
            for col in worksheet.columns:
                # Находим максимальную длину значения в столбце (включая заголовок)
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter # Получаем букву столбца (A, B, C...)                
                # Задаем ширину: максимальная длина + запас в 3 символа (минимум 12)
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
    return save_dir


if __name__ == '__main__':
    create_creative_stats_report()
