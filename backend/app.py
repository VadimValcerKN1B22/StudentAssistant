import os
import io
import json
from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ENV_PATH = os.path.join(BASE_DIR, ".env")

from dotenv import load_dotenv
load_dotenv(ENV_PATH)

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

INDEX_PATH = os.path.join(BASE_DIR, "indexed_files.json")

CACHE = {
    "gemini_files": [],
    "file_names": [],
    "file_bodies": {}
}

def load_index():
    if not os.path.exists(INDEX_PATH):
        print("❌ indexed_files.json не знайдено!")
        return False

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    CACHE["file_names"] = [f["name"] for f in data]
    CACHE["gemini_files"] = [genai.get_file(f["file_id"]) for f in data]

    for f in data:
        CACHE["file_bodies"][f["name"]] = bytes.fromhex(f["hex"])

    print(f"✅ Завантажено {len(CACHE['file_names'])} файлів з індексу.")
    return True

load_index()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    history = request.json.get("history", [])

    if not CACHE["gemini_files"]:
        return jsonify({"response": "Система завантажується. Спробуйте за 5–10 секунд."})

    files_str = ", ".join(CACHE["file_names"])

    system_prompt = f"""
Ти – StudentAssistant. Працюєш ТІЛЬКИ українською мовою.

Твоя база знань складається ТІЛЬКИ з цих PDF-файлів:
{files_str}

Інших джерел інформації в тебе немає.

ЗАГАЛЬНІ ПРАВИЛА
1. Відповідаєш звичайним текстом, БЕЗ Markdown:
   – без **жирного**,
   – без маркерів *, -, •,
   – без списків зі зірочками.
2. Форматуєш акуратно:
   – нумеровані списки виглядають так:
     1. Перший пункт
     2. Другий пункт
     3. Третій пункт
   – між логічними блоками — рівно один пустий рядок.

ФІЛЬТРАЦІЯ ЗА ГРУПОЮ
Користувач написав:
"{user_message}"

3. Якщо явно вказано шифр групи (наприклад KN1-B22):
   – відповідь містить ТІЛЬКИ дані для цієї групи;
   – не додавай жодного пункту інших груп;
   – якщо для групи нічого немає — чесно скажи про це.

4. Інформацію типу "для всіх груп" можна використовувати як спільну.

ФАЙЛИ
5. Якщо користувач просить файл/файли:
   повертаєш РІВНО такі рядки:
   [[DOWNLOAD: назва.pdf]]

ДЖЕРЕЛА
6. Якщо використовуєш дані з PDF — додай блок:
   [[SOURCE: назва.pdf | сторінка(и)]]

7. Якщо у pdf-файлах немає відповіді — скажи чесно.
"""

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.0},
            system_instruction=system_prompt
        )

        chat_session = [{"role": "user", "parts": CACHE["gemini_files"] + ["Start"]}]
        chat_session.append({"role": "model", "parts": ["Ready"]})

        for msg in history:
            chat_session.append({
                "role": "user" if msg["sender"] == "user" else "model",
                "parts": [msg["text"]]
            })

        chat_session.append({"role": "user", "parts": [user_message]})

        response = model.generate_content(chat_session)
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"response": f"Помилка: {str(e)}"})

@app.route("/download/<filename>")
def download_file(filename):
    if filename in CACHE["file_bodies"]:
        return send_file(
            io.BytesIO(CACHE["file_bodies"][filename]),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    return "Файл не знайдено", 404

@app.route("/clear", methods=["POST"])
def clear_chat():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
