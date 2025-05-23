import os
import google.generativeai as genai
import pandas as pd

# 設定 API 金鑰
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_reply(student_data):
    if not student_data:
        return "很抱歉，查無此學生資料，請確認姓名是否正確輸入。"

    student_info = "\n".join(f"{k}: {v}" for k, v in student_data.items())
    prompt = f"你是一名老師的助教，負責幫助老師回應關心學生的家長，請根據以下學生資料，簡單分析其學習與生活狀況，並給出簡短建議：\n\n{student_info}"

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
        # 🔍 1. 統整所有 Excel 成績
        all_scores = []
        for filename in os.listdir("data"):
            if filename.endswith(".xlsx"):
                try:
                    df = pd.read_excel(os.path.join("data", filename))
                    all_scores.append(df)
                except Exception as e:
                    print(f"[警告] 讀取 {filename} 錯誤：{e}")

        if not all_scores:
            return "⚠️ 無法讀取任何成績資料，請確認 data/ 資料夾是否有正確 Excel 檔案。"

        merged_scores = pd.concat(all_scores, ignore_index=True)
        scores_text = merged_scores.to_string(index=False)

        # 🔍 2. 整理所有 txt 評語
        note_texts = []
        notes_dir = "notes"
        if os.path.exists(notes_dir):
            for note_file in os.listdir(notes_dir):
                if note_file.endswith(".txt"):
                    try:
                        with open(os.path.join(notes_dir, note_file), encoding="utf-8") as f:
                            content = f.read().strip()
                            note_texts.append(f"【{note_file}】\n{content}")
                    except Exception as e:
                        print(f"[警告] 讀取 {note_file} 錯誤：{e}")

        notes_combined = "\n\n".join(note_texts) if note_texts else "（無老師評語紀錄）"

        # 🧠 3. 建立 Gemini 分析 Prompt
        prompt = f"""
你是一位智慧型學習助理。請根據以下資料幫助回答家長的提問，並以清楚、親切的方式回覆。

【家長提問】
{question_text}

【所有班級成績資料】
{scores_text}

【老師撰寫的學生評語】
{notes_combined}

請用條列或自然語句回答。
"""

        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print("❗ analyze_question_with_data 發生錯誤：", e)
        return f"❗ 系統在分析資料時發生錯誤：{e}"