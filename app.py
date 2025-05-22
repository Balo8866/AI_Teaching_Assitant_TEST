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

    # 使用 AI 辨識名字
    name = identify_student_name(message_text)

    if name:
        student_data = query_student(name)
        if isinstance(student_data, str) and "查無" in student_data:
            reply = f"查無 {name} 的資料，請確認姓名是否正確。"
        else:
            reply = generate_reply(student_data)
    else:
        # 若辨識不到名字，改用「問題分析模式」
        reply = analyze_question_with_data(message_text)

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
    if request.method == 'POST':
        name = request.form['name']
        comment = request.form['comment']
        today = date.today().isoformat()
        path = f"notes/{name}_{today}.txt"
        os.makedirs("notes", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(comment)
        saved = True
    return render_template("write_comment.html", saved=saved, name=name)

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
    table_html = ""
    error = None

    if request.method == 'POST':
        class_name = request.form['class_name']
        file_path = f"data/class_{class_name}.xlsx"

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            table_html = df.to_html(index=False)
        else:
            error = f"找不到班級 {class_name} 的成績檔案。"

    return render_template("view_class_scores.html", table_html=table_html, error=error)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
