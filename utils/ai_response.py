import os
import google.generativeai as genai

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
