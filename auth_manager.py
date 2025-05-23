# ✅ 新增檔案：auth_manager.py
# 用於管理 LINE 使用者與學生身分綁定狀態

import os
import json

BINDING_FILE = "auth/user_binding.json"
os.makedirs("auth", exist_ok=True)

# 初始化綁定檔案
if not os.path.exists(BINDING_FILE):
    with open(BINDING_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_binding():
    with open(BINDING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_binding(data):
    with open(BINDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def bind_user(user_id, student_id, student_name):
    data = load_binding()
    data[user_id] = {"id": student_id, "name": student_name}
    save_binding(data)

def unbind_user(user_id):
    data = load_binding()
    if user_id in data:
        del data[user_id]
        save_binding(data)

def get_bound_student(user_id):
    data = load_binding()
    return data.get(user_id)

def is_test_user(user_id):
    # 🔓 測試帳號清單
    return user_id in ["Uxxxxxxxxxxxx"]
