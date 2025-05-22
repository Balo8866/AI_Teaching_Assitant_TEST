import os
import pandas as pd

def query_student(name, folder_path='data'):
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith(".xlsx"):
                filepath = os.path.join(folder_path, filename)
                df = pd.read_excel(filepath)
                if "姓名" in df.columns:
                    result = df[df["姓名"] == name]
                    if not result.empty:
                        return result.to_dict("records")[0]
        return "查無此學生"
    except Exception as e:
        return f"資料載入錯誤：{e}"