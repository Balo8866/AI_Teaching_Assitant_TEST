# utils/data_handler.py
import pandas as pd

def query_student(name, filepath='data/class_scores.xlsx'):
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        return f"資料載入錯誤：{e}"

    result = df[df['姓名'] == name]
    if result.empty:
        return "查無此學生"
    return result.to_dict('records')[0]
