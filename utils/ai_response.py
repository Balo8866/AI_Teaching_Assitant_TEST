import os
import google.generativeai as genai
import pandas as pd

# 設定 API 金鑰
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_reply(student_data):
    if not student_data:
        return "很抱歉，查無此學生資料，請確認姓名是否正確輸入。"

    student_info = "\n".join(f"{k}: {v}" for k, v in student_data.items())
    prompt = f"請根據以下學生資料，簡單分析其學習與生活狀況，並給出簡短建議：\n\n{student_info}"

    try:
        # ✅ 改為使用 Flash 模型 + generate_content()
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("AI 發生錯誤：", e)
        return "目前 AI 回應配額已用完或服務異常，請稍後再試。"

# 這段程式碼是用來處理家長的提問，並根據學生的成績和老師的評語進行分析

def analyze_question_with_data(question_text):
    try:
        # 整理所有 Excel 成績資料
        all_scores = []
        for filename in os.listdir("data"):
            if filename.endswith(".xlsx"):
                df = pd.read_excel(os.path.join("data", filename))
                all_scores.append(df)
        merged_scores = pd.concat(all_scores, ignore_index=True)
        scores_text = merged_scores.to_string(index=False)

        # 整理所有老師評語
        note_texts = []
        if os.path.exists("notes"):
            for note_file in os.listdir("notes"):
                if note_file.endswith(".txt"):
                    with open(os.path.join("notes", note_file), encoding="utf-8") as f:
                        note_texts.append(f"【{note_file}】\n{f.read()}")
        notes_combined = "\n\n".join(note_texts)

        # 建立 prompt
        prompt = f"""
你是一位智慧型學習助理。請根據以下資料回答家長的提問：

【家長提問】
{question_text}

【所有班級成績資料】
{scores_text}

【老師撰寫的學生評語】
{notes_combined}

請用清楚、親切的語氣回答問題，並盡量引用數據與觀察依據。
"""

        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print("資料分析錯誤：", e)
        return "目前系統在分析資料時發生錯誤，請稍後再試。"
