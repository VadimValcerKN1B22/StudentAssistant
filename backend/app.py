import os
import json
from flask import Flask, render_template, request, jsonify, redirect
import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
INDEXED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indexed_files.json")

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment")

genai.configure(api_key=GEMINI_API_KEY)

CACHE = {"items": [], "downloads": {}}


def load_indexed_files():
    if not os.path.exists(INDEXED_PATH):
        return

    with open(INDEXED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = [{"name": name, "file_uri": uri, "download_url": ""} for name, uri in data.items()]
    else:
        items = data

    CACHE["items"] = items
    CACHE["downloads"] = {item["name"]: item.get("download_url", "") for item in items}


load_indexed_files()


def build_system_prompt(file_names):
    return f"""
Ти — StudentAssistant. Відповідаєш українською мовою.

Пиши звичайним текстом у формі абзаців. Не використовуй форматування, списки, маркери, символи *, -, #, _, [, ], ~ або декоративні елементи.

Використовуй тільки інформацію з PDF-файлів. Не вигадуй нічого.

Доступні файли: {", ".join(file_names)}.

Якщо відповідь містить інформацію з PDF, додай наприкінці:
[[SOURCE: назва.pdf | сторінки]]

Якщо користувач просить надіслати файл:
[[DOWNLOAD: назва.pdf]]

Якщо інформації немає:
У наявних PDF-файлах не знайдено інформації щодо цього запиту.
"""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    history = request.json.get("history", [])

    if not user_message:
        return jsonify({"response": "Введіть, будь ласка, запит."})

    if not CACHE["items"]:
        return jsonify({"response": "Система ще не має жодного проіндексованого файлу."})

    file_names = [item["name"] for item in CACHE["items"]]
    system_prompt = build_system_prompt(file_names)

    # ГОЛОВНЕ: модель, яка реально підтримує PDF
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        generation_config={"temperature": 0.0}
    )

    contents = []

    # Додаємо історію чату
    for msg in history:
        text = msg.get("text", "")
        if text:
            contents.append({
                "role": "user" if msg["sender"] == "user" else "model",
                "parts": [text]
            })

    # file_data (всі PDF)
    file_parts = [{"file_data": {"file_uri": item["file_uri"]}} for item in CACHE["items"]]

    contents.append({
        "role": "user",
        "parts": file_parts + [user_message]
    })

    try:
        response = model.generate_content(contents=contents, request_options={"timeout": 60})

        if not response.candidates:
            fb = getattr(response, "prompt_feedback", None)
            if fb and getattr(fb, "block_reason", None):
                return jsonify({"response": f"Відповідь заблоковано: {fb.block_reason}"})
            return jsonify({"response": "Модель не змогла сформувати відповідь."})

        text = response.text or "Модель не повернула текст."
        return jsonify({"response": text})

    except Exception as e:
        print("\n\n================ REAL MODEL ERROR ================\n")
        print(e)
        print("\n=================================================\n")

        return jsonify({"response": "Помилка моделі: " + str(e)})


@app.route("/download/<path:filename>")
def download_file(filename):
    filename = filename.strip()

    normalized = (
        filename.replace("%20", " ")
        .replace("’", "'")
        .replace("`", "'")
        .replace("ʼ", "'")
    )

    for real_name, url in CACHE["downloads"].items():
        if real_name.lower() == normalized.lower():
            return redirect(url)

    return "Файл не знайдено у базі", 404


@app.route("/clear", methods=["POST"])
def clear_chat():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
