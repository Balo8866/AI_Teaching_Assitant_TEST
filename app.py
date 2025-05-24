from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
import pandas as pd
import google.generativeai as genai

from datetime import date

from utils.ai_response import generate_reply, analyze_question_with_data
from utils.data_handler import query_student

from difflib import get_close_matches


from auth_manager import (
    bind_user, unbind_user,
    get_bound_student, is_test_user
)


# 載入 .env
load_dotenv()

# 設定 Gemini 金鑰
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/")
def index():
    return "AI 助教系統運行中 ✅"

@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ➕ AI 辨識學生姓名函式
def identify_student_name(message_text):
    # 從所有班級成績檔取得學生姓名清單
    all_names = []
    data_folder = "data"

    for filename in os.listdir(data_folder):
        if filename.endswith(".xlsx"):
            filepath = os.path.join(data_folder, filename)
            try:
                df = pd.read_excel(filepath)
                if "姓名" in df.columns:
                    all_names.extend(
                    df["姓名"]
                    .dropna()
                    .astype(str)
                    .str.replace("　", "")  # 移除全形空白
                    .str.replace(" ", "")   # 移除半形空白
                    .str.strip()
                    .tolist()
                )

            except Exception as e:
                print(f"[錯誤] 讀取 {filename} 發生錯誤：{e}")

    all_names = list(set(all_names))  # 去除重複

    # 建 AI Prompt
    prompt = f"""以下是家長的話語：「{message_text}」
請從中找出提到的學生姓名。以下是已知學生名單：
{', '.join(all_names)}
請只輸出其中一個姓名（若無則輸出「無」）：
"""

    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        name_raw = (
        response.text
            .replace("　", "")
            .replace(" ", "")
            .strip()
        )

        # 模糊比對：找最接近的學生姓名
        matched = get_close_matches(name_raw, all_names, n=1, cutoff=0.6)
        if matched:
            print(f"[DEBUG] 原始輸入：{message_text}")
            print(f"[DEBUG] AI 回傳：{name_raw}")
            print(f"[DEBUG] 模糊比對成功：{matched[0]}")
            return matched[0]
        else:
            print(f"[DEBUG] 模糊比對失敗：{name_raw} 不存在")
            return None

    except Exception as e:
        print("辨識學生姓名錯誤：", e)
        return None



# 修改後的主邏輯
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message_text = event.message.text.strip()
    user_id = event.source.user_id

# 自動登出關鍵字
    logout_keywords = ["我沒有想問", "我沒有其他問題", "沒事了", "沒有問題", "結束", "不用了", "登出", "我問完了"]
    if any(keyword in message_text for keyword in logout_keywords):
        unbind_user(user_id)
        reply = "✅ 已為您結束查詢並登出，如需查詢其他學生請重新輸入「學號 姓名」進行驗證。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return


    # ✅ 若為測試帳號或已驗證
    bound = get_bound_student(user_id)
    if is_test_user(user_id) or bound:

        # 測試帳號直接啟用 AI 模式
        if is_test_user(user_id):
            reply = analyze_question_with_data(message_text)
        else:
        # 僅允許查詢綁定學生
            if bound["name"] in message_text or bound["id"] in message_text:
                reply = analyze_question_with_data(message_text, default_student=bound["name"])
            else:
                reply = f"⚠️ 僅允許查詢 {bound['name']} 的資料，如需查詢其他人請先登出。"



    else:
        # 若格式正確（學號+姓名）
        parts = message_text.split()
        if len(parts) == 2:
            student_id, student_name = parts
            result = query_student(student_name)
            if isinstance(result, dict):  # 查到資料才綁定
                bind_user(user_id, student_id, student_name)
                reply = f"✅ 驗證成功，您可查詢 {student_name} 的資料。"
            else:
                reply = "❌ 驗證失敗，請確認學號與姓名是否正確。"
        else:
            reply = (
                "👋 歡迎使用學生成績查詢系統，請先完成身份驗證。\n"
                "請輸入「學號 姓名」，例如：A001 吳志強"
            )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

@app.route("/teacher", methods=['GET', 'POST'])
def teacher_input():
    filepath = 'data/class_scores.xlsx'
    if request.method == 'POST':
        name = request.form['name']
        note = request.form['note']
        df = pd.read_excel(filepath)
        df.loc[df['姓名'] == name, '老師備註'] = note
        df.to_excel(filepath, index=False)
        return f"已更新 {name} 的備註"
    return render_template("teacher_input.html")

from datetime import date

@app.route("/write_comment", methods=['GET', 'POST'])
def write_comment():
    saved = False
    name = None

    # 🔸 讀取所有班級與學生名單
    student_data = {}
    for filename in os.listdir("data"):
        if filename.endswith(".xlsx"):
            class_name = filename.replace("class_", "").replace(".xlsx", "")
            df = pd.read_excel(os.path.join("data", filename))
            if "姓名" in df.columns:
                student_data[class_name] = df["姓名"].dropna().tolist()

    if request.method == 'POST':
        name = request.form['name']
        comment = request.form['comment']
        today = date.today().isoformat()
        os.makedirs("notes", exist_ok=True)
        path = f"notes/{name}_{today}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(comment)
        saved = True

    return render_template("write_comment.html", saved=saved, name=name, student_data=student_data)


@app.route("/teacher_dashboard")
def teacher_dashboard():
    return render_template("teacher_dashboard.html")

@app.route("/upload_scores", methods=['GET', 'POST'])
def upload_scores():
    success = False
    filename = None

    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            filename = file.filename
            save_path = os.path.join('data', filename)
            os.makedirs('data', exist_ok=True)
            file.save(save_path)
            success = True

    return render_template("upload_scores.html", success=success, filename=filename)

@app.route("/view_class_scores", methods=['GET', 'POST'])
def view_class_scores():
    error = None
    df = None
    selected_class = None

    # ⬇️ 動態讀取班級清單
    class_list = []
    for filename in os.listdir("data"):
        if filename.endswith(".xlsx") and filename.startswith("class_"):
            class_name = filename.replace("class_", "").replace(".xlsx", "")
            class_list.append(class_name)

    if request.method == 'POST':
        action = request.form.get("action")
        selected_class = request.form.get("class_name")
        file_path = f"data/class_{selected_class}.xlsx"

        if not os.path.exists(file_path):
            error = f"找不到班級 {selected_class} 的成績檔案。"
        else:
            if action == "load":
                df = pd.read_excel(file_path)
            elif action == "save":
                df_old = pd.read_excel(file_path)
                new_data = []
                for i in range(len(df_old)):
                    row_data = {}
                    for col in df_old.columns:
                        key = f"cell_{i}_{col}"
                        row_data[col] = request.form.get(key)
                    new_data.append(row_data)
                df = pd.DataFrame(new_data)
                df.to_excel(file_path, index=False)

    return render_template("view_class_scores.html", df=df, error=error, selected_class=selected_class, class_list=class_list)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
