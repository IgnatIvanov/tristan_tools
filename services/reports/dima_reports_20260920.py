import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import range_boundaries
from openpyxl.cell import MergedCell

import pandas as pd
from datetime import date
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import numpy as np
import os
import shutil
from pathlib import Path
# 
from services.arabica.get_dolphin_metrics import get_dolphin_metrics



def copy_cell_range(ws, start_row, start_col, end_row, end_col, dest_row, dest_col):
    """
    Копирует прямоугольный диапазон ячеек из одной части листа в другую.
    Переносит: значения, шрифты, заливку, границы, объединения И ширину колонок.
    """
    row_offset = dest_row - start_row
    col_offset = dest_col - start_col

    # 1. Сначала обрабатываем и копируем структуру объединения ячеек (Merge Cells)
    for merge_range in list(ws.merged_cells.ranges):
        min_col, min_row, max_col, max_row = merge_range.bounds
        
        # Проверяем, попадает ли объединение в исходный диапазон
        if min_row >= start_row and max_row <= end_row and min_col >= start_col and max_col <= end_col:
            new_min_row = min_row + row_offset
            new_max_row = max_row + row_offset
            new_min_col = min_col + col_offset
            new_max_col = max_col + col_offset
            
            # Применяем объединение на новом месте
            ws.merge_cells(
                start_row=new_min_row, start_column=new_min_col,
                end_row=new_max_row, end_column=new_max_col
            )

    # 2. Копируем значения, формулы и стили по ячейкам
    for r in range(start_row, end_row + 1):
        for c in range(start_col, end_col + 1):
            src_cell = ws.cell(row=r, column=c)
            
            tgt_row = r + row_offset
            tgt_col = c + col_offset
            tgt_cell = ws.cell(row=tgt_row, column=tgt_col)
            
            # Проверяем, не является ли целевая ячейка MergedCell
            if not isinstance(tgt_cell, MergedCell):
                tgt_cell.value = src_cell.value
            
            # Копируем стили
            if src_cell.has_style:
                tgt_cell.font = Font(
                    name=src_cell.font.name, size=src_cell.font.size, 
                    bold=src_cell.font.bold, italic=src_cell.font.italic, 
                    color=src_cell.font.color
                )
                tgt_cell.fill = PatternFill(
                    fill_type=src_cell.fill.fill_type, 
                    start_color=src_cell.fill.start_color, 
                    end_color=src_cell.fill.end_color
                )
                tgt_cell.border = Border(
                    left=src_cell.border.left, right=src_cell.border.right, 
                    top=src_cell.border.top, bottom=src_cell.border.bottom
                )
                tgt_cell.alignment = Alignment(
                    horizontal=src_cell.alignment.horizontal, 
                    vertical=src_cell.alignment.vertical, 
                    wrap_text=src_cell.alignment.wrap_text
                )
                tgt_cell.number_format = src_cell.number_format

    # 3. ДОБАВЛЕНО: Копируем ширину колонок
    for c in range(start_col, end_col + 1):
        src_letter = get_column_letter(c)
        tgt_letter = get_column_letter(c + col_offset)
        
        # Проверяем, задана ли ширина для исходной колонки
        if src_letter in ws.column_dimensions:
            src_width = ws.column_dimensions[src_letter].width
            # Если ширина нестандартная (изменена пользователем в шаблоне)
            if src_width is not None:
                ws.column_dimensions[tgt_letter].width = src_width


def delete_cols_with_merged_ranges(ws, start_col, end_col):
    """
    Абсолютно стабильное удаление столбцов.
    Изолирует расчет координат от внутренних процессов сдвига openpyxl.
    """
    amount = end_col - start_col + 1
    surviving_merges = []
    
    # 1. СКАНИРОВАНИЕ И РАСЧЕТ (Делаем строго ДО удаления колонок)
    for merge in list(ws.merged_cells.ranges):
        min_col, min_row, max_col, max_row = merge.bounds
        
        # Сценарий А: Объединение находится полностью ЛЕВЕЕ удаляемой зоны
        # Оно остается в полной безопасности на своих старых координатах
        if max_col < start_col:
            surviving_merges.append((min_row, min_col, max_row, max_col))
            
        # Сценарий Б: Объединение находится полностью ПРАВЕЕ удаляемой зоны
        # Математически рассчитываем его будущие новые координаты (сдвиг влево)
        elif min_col > end_col:
            new_min_col = min_col - amount
            new_max_col = max_col - amount
            surviving_merges.append((min_row, new_min_col, max_row, new_max_col))
            
        # Сценарий В: Любое пересечение с удаляемой зоной (полное или частичное)
        # Такие мерджи мы просто игнорируем (они не идут в surviving_merges),
        # что физически означает их удаление.

    # 2. ОЧИСТКА И ФИЗИЧЕСКОЕ УДАЛЕНИЕ СТОЛБЦОВ
    # Обнуляем реестр мерджей, чтобы openpyxl не пытался ничего сдвигать сам
    ws.merged_cells.ranges = []
    
    # Теперь физически удаляем колонки (данные и стили обычных ячеек уедут влево)
    ws.delete_cols(idx=start_col, amount=amount)
    
    # 3. ВОССТАНОВЛЕНИЕ СТРУКТУРЫ
    # Записываем выжившие и пересчитанные объединения обратно на лист
    for min_row, min_col, max_row, max_col in surviving_merges:
        ws.merge_cells(
            start_row=min_row, start_column=min_col,
            end_row=max_row, end_column=max_col
        )

def write_dataframe_by_position(ws, df, start_row, start_col):
    """
    Записывает данные из pandas DataFrame в ячейки openpyxl построчно,
    начиная со стартовой позиции (start_row, start_col), игнорируя названия колонок.
    
    :param ws: Рабочий лист openpyxl
    :param df: Ваш pandas DataFrame с данными
    :param start_row: Строка первой ячейки для данных (int)
    :param start_col: Столбец первой ячейки для данных (int)
    """
    # Превращаем DataFrame в обычный список списков (матрицу значений)
    data_matrix = df.values
    
    for r_idx, row_data in enumerate(data_matrix):
        for c_idx, value in enumerate(row_data):
            # Вычисляем точные координаты текущей ячейки на листе
            current_row = start_row + r_idx
            current_col = start_col + c_idx
            
            cell = ws.cell(row=current_row, column=current_col)
            
            # Проверяем на MergedCell (чтобы не упасть в ошибку, если ячейка объединена)
            if not isinstance(cell, MergedCell):
                # Если в pandas значение NaN (пустое), записываем None, чтобы в Excel ячейка была пустой
                if pd.isna(value):
                    cell.value = None
                else:
                    cell.value = value


def get_total_report_by_date(
        df: pd.DataFrame,
        start_date: date,
        end_date: date,
        group_by_cols : list
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
    return total_report

def input_subtable_data(
        df: pd.DataFrame,
        ws: openpyxl.Workbook,
        header_text: str,
        header_start_row: int, header_start_col: int,
        header_end_row: int, header_end_col: int,
        start_col: int,
        start_row: int,
):
    # Подготовка общего отчёта по образцу dima_total_20260920.xlsx
    # 
    # *. Заполнение общих данных
    # Начинаем с копирования шапки таблицы в верх правее от оставшихся примеров шапки
    # current_col = 10
    # current_row = 1
    current_col = start_col
    current_row = start_row
    copy_cell_range(
        ws=ws,
        # start_row=1, start_col=2,  # Начало: B1
        start_row=header_start_row, start_col=header_start_col,  # Начало: B1
        end_row=header_end_row, end_col=header_end_col,     # Конец:  D10
        dest_row=current_row, dest_col=current_col     # Куда: J1 
    )
    # Обновляем текст заголовка
    cell = ws.cell(row=current_row, column=current_col)
    cell.value = header_text
    current_row += 2  # Смещаем строку записи на две строки, сразу ниже шапки
    # 
    # Размещение данных в таблице
    write_dataframe_by_position(
        ws=ws,
        df=df,
        start_row=current_row, 
        start_col=current_col
    )

    # Сохраняем финальный результат
    # wb.save("report_with_data.xlsx")


def prepare_total_report(
        df:pd.DataFrame,
        start_date: dt,
        end_date: dt,
        report_file_name: str,
):
    # 
    # *. копирование файла образца для работы
    parent_dir = Path.cwd().parent
    # example_path = os.path.join(parent_dir, 'examples', 'dima_total_20260920.xlsx')
    example_path = os.path.join('examples', 'dima_total_20260920.xlsx')
    # 
    # report_dir = os.path.join(parent_dir, 'google_drive_out', 'dolphin_1', 'Дима')
    report_dir = os.path.join('documents_out', 'google_drive_out', 'dolphin_1', 'Дима')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, report_file_name)
    shutil.copy(example_path, report_path)
    # 
    # *. Очистить данные образца с таблиц второй и третьей колонки
    wb = openpyxl.load_workbook(report_path)
    ws = wb.active
    start_col = 10  # Столбец J
    amount_to_delete = 17  # Удаляем две колонки таблиц
    # ws.delete_cols(idx=start_col, amount=amount_to_delete)
    delete_cols_with_merged_ranges(ws, start_col=start_col, end_col=(start_col+amount_to_delete))

    
    _filter = ((df['metrics_date']>=start_date) & (df['metrics_date']<=end_date))
    df = df[_filter]

    # 
    # Подготовка данных для записи
    # Верхняя часть отчёта с Дата-Спенд
    # df['metrics_date'] = df['metrics_date'].apply(dt.fromisoformat)
    group_by_cols=['metrics_date']
    total_date_report = get_total_report_by_date(
        df,
        start_date,
        end_date,
        group_by_cols=group_by_cols
    )
    total_date_report = total_date_report.sort_values(by=group_by_cols)
    # total_date_report['metrics_date'] = total_date_report['metrics_date'].apply(lambda x: x.date())

    start_col = 10
    current_col = 10
    start_row = 1

    input_subtable_data(
        df=total_date_report,
        ws=ws,
        header_text='Общий',
        header_start_row=1, header_start_col=1,
        header_end_row=2, header_end_col=8,
        start_col=current_col,
        start_row=start_row
    )

    tier_list = list(df['tier'].unique())
    for tier_name in tier_list:
        current_col += 9
        df_tier = df[df['tier']==tier_name]
        group_by_cols=['metrics_date']
        total_date_report = get_total_report_by_date(
            df_tier,
            start_date,
            end_date,
            group_by_cols=group_by_cols
        )
        total_date_report = total_date_report.sort_values(by=group_by_cols)
        # total_date_report['metrics_date'] = total_date_report['metrics_date'].apply(lambda x: x.date())    
        # 
        input_subtable_data(
            df=total_date_report,
            ws=ws,
            header_text=tier_name,
            header_start_row=1, header_start_col=1,
            header_end_row=2, header_end_col=8,
            start_col=current_col,
            start_row=start_row
        )

    # ---------------------------------------
    # нижняя часть отчёта с крео-спенд
    # 
    # Смещаем начало записи в левую часть ниже на 25 строк первой записанной общей таблицы
    current_col = start_col
    start_row += ( 25 + len(list(df['metrics_date'].unique())) )
    # 
    group_by_cols=['art_name']
    total_date_report = get_total_report_by_date(
        df,
        start_date,
        end_date,
        group_by_cols=group_by_cols
    )
    total_date_report = total_date_report.sort_values(by=group_by_cols)
    # total_date_report['art_name'] = total_date_report['art_name'].apply(lambda x: x.date())

    # start_col = 10
    # current_col = 10
    # start_row = 1

    input_subtable_data(
        df=total_date_report,
        ws=ws,
        header_text='Общий',
        header_start_row=29, header_start_col=1,
        header_end_row=30, header_end_col=8,
        start_col=current_col,
        start_row=start_row
    )

    # tier_list = list(df['tier'].unique())
    for tier_name in tier_list:
        current_col += 9
        df_tier = df[df['tier']==tier_name]
        group_by_cols=['art_name']
        total_date_report = get_total_report_by_date(
            df_tier,
            start_date,
            end_date,
            group_by_cols=group_by_cols
        )
        total_date_report = total_date_report.sort_values(by=group_by_cols)
        # total_date_report['art_name'] = total_date_report['art_name'].apply(lambda x: x.date())    
        # 
        input_subtable_data(
            df=total_date_report,
            ws=ws,
            header_text=tier_name,
            header_start_row=29, header_start_col=1,
            header_end_row=30, header_end_col=8,
            start_col=current_col,
            start_row=start_row
        )

    # Удаляем оставшиеся образцы, первые 9 колонок
    delete_cols_with_merged_ranges(ws, start_col=1, end_col=9)

    # 
    # Финальное сохранение отчёта
    wb.save(report_path)

def prepare_buyer_report(
        df:pd.DataFrame,
        start_date: dt,
        end_date: dt,
        report_file_name: str,
):
    # 
    # *. копирование файла образца для работы
    
    # 
    parent_dir = Path.cwd().parent
    # example_path = os.path.join(parent_dir, 'examples', 'dima_buyer_20260920.xlsx')
    example_path = os.path.join('examples', 'dima_buyer_20260920.xlsx')
    # 
    # report_dir = os.path.join(parent_dir, 'google_drive_out', 'dolphin_1', 'Дима')
    report_dir = os.path.join('documents_out', 'google_drive_out', 'dolphin_1', 'Дима')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, report_file_name)
    shutil.copy(example_path, report_path)
    # 
    # *. Очистить данные образца с таблиц второй и третьей колонки
    wb = openpyxl.load_workbook(report_path)
    ws = wb.active
    start_col = 10  # Столбец J
    amount_to_delete = 17  # Удаляем две колонки таблиц
    # ws.delete_cols(idx=start_col, amount=amount_to_delete)
    delete_cols_with_merged_ranges(ws, start_col=start_col, end_col=(start_col+amount_to_delete))

    
    _filter = ((df['metrics_date']>=start_date) & (df['metrics_date']<=end_date))
    df = df[_filter]
    if df.shape[0] == 0: 
        os.remove(report_path)
        return

    # 
    # Подготовка данных для записи
    # Верхняя часть отчёта с Дата-Спенд
    # df['metrics_date'] = df['metrics_date'].apply(dt.fromisoformat)
    group_by_cols=['metrics_date', 'buyer']
    total_date_report = get_total_report_by_date(
        df,
        start_date,
        end_date,
        group_by_cols=group_by_cols
    )
    total_date_report = total_date_report.sort_values(by=group_by_cols)
    # total_date_report['metrics_date'] = total_date_report['metrics_date'].apply(lambda x: x.date())

    start_col = 11
    current_col = 11
    start_row = 1

    input_subtable_data(
        df=total_date_report,
        ws=ws,
        header_text='Общий',
        header_start_row=1, header_start_col=1,
        header_end_row=2, header_end_col=9,
        start_col=current_col,
        start_row=start_row
    )

    tier_list = list(df['tier'].unique())
    for tier_name in tier_list:
        current_col += 10
        df_tier = df[df['tier']==tier_name]
        group_by_cols=['metrics_date', 'buyer']
        total_date_report = get_total_report_by_date(
            df_tier,
            start_date,
            end_date,
            group_by_cols=group_by_cols
        )
        total_date_report = total_date_report.sort_values(by=group_by_cols)
        # total_date_report['metrics_date'] = total_date_report['metrics_date'].apply(lambda x: x.date())    
        # 
        input_subtable_data(
            df=total_date_report,
            ws=ws,
            header_text=tier_name,
            header_start_row=1, header_start_col=1,
            header_end_row=2, header_end_col=9,
            start_col=current_col,
            start_row=start_row
        )

    # ---------------------------------------
    # нижняя часть отчёта с крео-спенд
    # 
    # Смещаем начало записи в левую часть ниже на 25 строк первой записанной общей таблицы
    current_col = start_col
    start_row += ( 25 + len(list(df['metrics_date'].unique())) )
    # 
    group_by_cols=['art_name', 'buyer']
    total_date_report = get_total_report_by_date(
        df,
        start_date,
        end_date,
        group_by_cols=group_by_cols
    )
    total_date_report = total_date_report.sort_values(by=group_by_cols)
    # total_date_report['art_name'] = total_date_report['art_name'].apply(lambda x: x.date())

    # start_col = 10
    # current_col = 10
    # start_row = 1

    input_subtable_data(
        df=total_date_report,
        ws=ws,
        header_text='Общий',
        header_start_row=29, header_start_col=1,
        header_end_row=30, header_end_col=9,
        start_col=current_col,
        start_row=start_row
    )

    # tier_list = list(df['tier'].unique())
    for tier_name in tier_list:
        current_col += 10
        df_tier = df[df['tier']==tier_name]
        group_by_cols=['art_name', 'buyer']
        total_date_report = get_total_report_by_date(
            df_tier,
            start_date,
            end_date,
            group_by_cols=group_by_cols
        )
        total_date_report = total_date_report.sort_values(by=group_by_cols)
        # total_date_report['art_name'] = total_date_report['art_name'].apply(lambda x: x.date())    
        # 
        input_subtable_data(
            df=total_date_report,
            ws=ws,
            header_text=tier_name,
            header_start_row=29, header_start_col=1,
            header_end_row=30, header_end_col=9,
            start_col=current_col,
            start_row=start_row
        )

    # Удаляем оставшиеся образцы, первые 9 колонок
    delete_cols_with_merged_ranges(ws, start_col=1, end_col=10)

    # 
    # Финальное сохранение отчёта
    wb.save(report_path)









def main():
    df = get_dolphin_metrics()
    # 

    def fill_buyer(x: pd.Series):
        if type(x.url_params) == float: return 'Plex1'
        if 'buyer_name' not in x.url_params: return 'Plex1'
        params = str(x.url_params).split('&')
        for p in params:
            if 'buyer_name' in p:
                return p.replace('buyer_name=', '')

    df['buyer'] = df.apply(fill_buyer, axis=1)




    df['metrics_date'] = df['metrics_date'].apply(lambda x: x.date())
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
        # print('dt_start', dt_start)
        # print('dt_end', dt_end)
        # print('dt_max', dt_max)

    for p in periods:
        prepare_total_report(
            df,
            p['start'],
            p['end'],
            report_file_name=f'Общий {p["start"].year}.{p["start"].month:02d}.xlsx',
        )
        buyer_list = list(df['buyer'].unique())
        for buyer_name in buyer_list:
            df_buyer = df[df['buyer'] == buyer_name]
            prepare_buyer_report(
                df_buyer,
                p['start'],
                p['end'],
                report_file_name=f'Баер {buyer_name} {p["start"].year}.{p["start"].month:02d}.xlsx',
            )

if __name__ == '__main__':
    main()