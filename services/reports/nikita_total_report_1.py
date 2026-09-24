import os
import shutil
import calendar
import pandas as pd
import numpy as np
from tqdm import tqdm
from pathlib import Path
from datetime import datetime as dt
from datetime import timedelta
from sqlalchemy import create_engine, text
# 
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import range_boundaries
from openpyxl.cell import MergedCell
import copy
from openpyxl.cell.cell import Cell
# 
from services.arabica.get_combined_metrics import get_combined_metrics


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

            tgt_cell.font = copy.copy(src_cell.font)
            
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


def prepare_report():
    df = get_combined_metrics()
    # 
    df.rename(
        inplace=True,
        columns={
            'spent': 'spend',
        },
    )
    report = df.groupby('interval_date', as_index=False).agg({
        'spend': 'sum',
        # 'clicks': 'sum',
        'sub_count': 'sum',
        'decline_sub_count': 'sum',
        'dialog_count': 'sum',
        # 'regs': 'sum',
        'ftd_count': 'sum',
        'ftd_revenue': 'sum',
    })
    # total_report['click_cost'] = (total_report['spend'] / total_report['clicks']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    report['sub_cost'] = (report['spend'] / report['sub_count']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    # report['decline_sub_cost'] = (report['spend'] / report['sub_count']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    report['dialog_cost'] = (report['spend'] / report['dialog_count']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    # total_report['reg_cost'] = (total_report['spend'] / total_report['regs']).round(2).replace([np.inf, -np.inf], np.nan).fillna(0)
    report['ftd_cost'] = (report['spend'] / report['ftd_count']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    report['cr_dialog_to_fd'] = (report['ftd_count'] / report['dialog_count']).replace([np.inf, -np.inf], np.nan).round(4).fillna(0) 
    # report['cr_dialog_to_fd'] = report['cr_dialog_to_fd'].apply(lambda x: f'{x:.2f}%')
    # report['purchase_cost'] = (report['spend'] / report['purchase']).replace([np.inf, -np.inf], np.nan).round(2).fillna(0)
    report['spend'] = report['spend'].round(2)
    report['interval_date'] = report['interval_date'].apply(lambda x: x.date())
    report['date_2'] = report['interval_date']
    report['sends'] = ''
    report['spend_farm'] = ''
    report['sl'] = ''
    report['cpsl'] = ''
    report['a_comm'] = ''
    report = report[[
        'interval_date',
        'sends',
        'spend',
        'spend_farm',
        'sub_count',
        'sub_cost',
        'decline_sub_count',
        'dialog_count',
        'dialog_cost',
        'sl',
        'cpsl',
        'ftd_count',
        'ftd_cost',
        'cr_dialog_to_fd',
        'date_2',
        'a_comm',
        'ftd_revenue'
    ]]
    report.sort_values(by='interval_date', inplace=True)
    # 
    # *. копирование файла образца для работы
    parent_dir = Path.cwd().parent
    example_path = os.path.join('examples', 'nikita_table1.xlsx')
    # 
    report_dir = os.path.join('documents_out', 'google_drive_out', 'dolphin_1', 'Никита')
    os.makedirs(report_dir, exist_ok=True)
    report_file_name = 'Tristan_2026.xlsx'
    report_path = os.path.join(report_dir, report_file_name)
    shutil.copy(example_path, report_path)
    # 
    wb = openpyxl.load_workbook(report_path)
    ws = wb.active
    # 
    english_months = (
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    )

    start_col = 1
    start_row = 2

    data_matrix = report.values
    data_matrix = np.append(data_matrix, [[data_matrix[-1][0] + timedelta(days=31)] * len(data_matrix[0])], axis=0)

    # 1. ЗАПОМИНАЕМ ИСХОДНЫЕ СТИЛИ НАПРЯМУЮ ИЗ НАСТРОЕК СТОЛБЦОВ EXCEL
    # Это гарантирует, что мы возьмем цвет, даже если физических ячеек в строке 3 еще не существует
    column_styles = {}
    num_cols = len(data_matrix[0]) if len(data_matrix) > 0 else 0

    for c_idx in range(num_cols):
        col_num = start_col + c_idx
        # Получаем буквенное имя колонки (например, 1 -> 'A', 2 -> 'B')
        col_letter = openpyxl.utils.get_column_letter(col_num)
        
        # Извлекаем глобальные стили, назначенные на весь столбец целиком
        col_dim = ws.column_dimensions[col_letter]
        
        # Если на столбец не назначено индивидуальное оформление, 
        # возьмем стиль из строки шапки (строка 2, прямо над началом данных), чтобы подстраховаться
        header_cell = ws.cell(row=start_row - 1, column=col_num)
        
        column_styles[col_num] = {
            'fill': copy.copy(col_dim.fill if col_dim.fill else header_cell.fill),
            'font': copy.copy(col_dim.font if col_dim.font else header_cell.font),
            'border': copy.copy(col_dim.border if col_dim.border else header_cell.border),
            'alignment': copy.copy(col_dim.alignment if col_dim.alignment else header_cell.alignment),
            'number_format': col_dim.number_format if col_dim.number_format else header_cell.number_format
        }


    prev_date_month = -1
    header_start_col = 1
    header_start_row = 2
    header_end_col = 19
    header_end_row = 2
    current_row = 2
    current_col = 1
    columns_sums = []  # Итоги по месяцу, обновляются каждую запись
    subtotal_font = Font(bold=True, size=14, name="Calibri")

    # 2. ОСНОВНОЙ ЦИКЛ ЗАПИСИ
    for r_idx, row_data in enumerate(data_matrix):    
        # 
        if (prev_date_month != row_data[0].month) and (current_row != 2):
            for c_idx, value in enumerate(columns_sums):
                # current_row = start_row + r_idx
                current_col = start_col + c_idx
                
                cell = ws.cell(row=current_row, column=current_col)
                
                # Записываем значение (для обычных ячеек и главных ячеек объединений)
                if type(cell) is Cell:
                    if pd.isna(value):
                        cell.value = None
                    else:
                        cell.value = value
                    
                    # Принудительно возвращаем сохраненный стиль этой колонки
                    style = column_styles[current_col]
                    if style['fill']: cell.fill = style['fill']
                    # if style['font']: cell.font = style['font']
                    if style['font']: cell.font = subtotal_font
                    if style['border']: cell.border = style['border']
                    if style['alignment']: cell.alignment = style['alignment']
                    if style['number_format']: cell.number_format = style['number_format']
            current_row += 1
        # 
        if r_idx == len(data_matrix) - 1: break
        # 
        if prev_date_month != row_data[0].month:
            # Если начинаем записывать новый месяц, то нужно добавить итоги и шапку для следующего месяца
            # 
            columns_sums = [0] * len(row_data)  # Объявляем нулевые значения итогов
            # 
            copy_cell_range(
                ws=ws,
                # start_row=1, start_col=2,  # Начало: B1
                start_row=header_start_row, start_col=header_start_col,  # Начало: B1
                end_row=header_end_row, end_col=header_end_col,     # Конец:  D10
                dest_row=current_row, dest_col=1     # Куда: J1 
            )
            # Отдельно копирую высоту строки
            source_height = ws.row_dimensions[2].height
            ws.row_dimensions[current_row].height = source_height
            # 
            cell = ws.cell(row=current_row, column=1)
            cell.value = english_months[row_data[0].month]
            # print(row_data[0].strftime("%B"))
            current_row += 1
        # 
        for c_idx, value in enumerate(row_data):
            # current_row = start_row + r_idx
            current_col = start_col + c_idx
            
            cell = ws.cell(row=current_row, column=current_col)
            
            # Записываем значение (для обычных ячеек и главных ячеек объединений)
            if type(cell) is Cell:
                if pd.isna(value):
                    cell.value = None
                else:
                    cell.value = value
                
                # Принудительно возвращаем сохраненный стиль этой колонки
                style = column_styles[current_col]
                if style['fill']: cell.fill = style['fill']
                if style['font']: cell.font = style['font']
                if style['border']: cell.border = style['border']
                if style['alignment']: cell.alignment = style['alignment']
                if style['number_format']: cell.number_format = style['number_format']
            # 
            # Обновление значения в подитогах месяца
            if c_idx == 0:
                columns_sums[c_idx] = 'Total'
                continue
            if c_idx == 13:  ## Расчёт CR
                if not columns_sums[8]: columns_sums[c_idx] = 0
                else: columns_sums[c_idx] = round(columns_sums[11] / columns_sums[7], 4)
                continue
            if (c_idx == 14) or (type(value) == str):
                columns_sums[c_idx] = ''
                continue
            columns_sums[c_idx] += value
        prev_date_month = row_data[0].month  # Сохранение месяца даты в записанной строке
        current_row += 1

    wb.save(report_path)




if __name__ == '__main__':
    prepare_report()
