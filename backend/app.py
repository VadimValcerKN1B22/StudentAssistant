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
genai.configure(api_key=GEMINI_API_KEY)

CACHE = {
    "gemini_files": [],
    "file_names": [],
    "downloads": {}
}

def load_indexed_files():
    if not os.path.exists(INDEXED_PATH):
        print("indexed_files.json не знайдено")
        return

    with open(INDEXED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = [{"name": name, "file_uri": uri, "download_url": ""} for name, uri in data.items()]
    else:
        items = data

    CACHE["gemini_files"] = [item["file_uri"] for item in items]
    CACHE["file_names"] = [item["name"] for item in items]
    CACHE["downloads"] = {item["name"]: item.get("download_url", "") for item in items}

    print(f"Завантажено з indexed_files.json: {len(CACHE['file_names'])} файлів")

load_indexed_files()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    history = request.json.get("history", [])

    if not CACHE["gemini_files"]:
        return jsonify({"response": "Система ще не має жодного проіндексованого файлу. Зверніться до адміністратора."})

    files_str = ", ".join(CACHE["file_names"])

    system_prompt = f"""
Ти – StudentAssistant. Працюєш ТІЛЬКИ українською мовою.

Твоя база знань складається ТІЛЬКИ з таких PDF-файлів:
pravyla-2025.pdf
Додаток 2025 (1).pdf
Додаток_до_розп_про_інформ_пакети_1.pdf
Інф_пакет_2025_комп_науки,_бакалавр_1.pdf
Інформація про викладачів.pdf
Комп'ютерні_науки_бакалавр_2025_1.pdf
Комп'ютерні_науки_магістр_2025_1.pdf
Новини.pdf
Розпорядження_Інформаційні_пакети_1.pdf

Інших джерел у тебе НЕ ІСНУЄ. Відповідаєш ТІЛЬКИ на основі цих файлів. Нічого не вигадуєш.

ЗАГАЛЬНІ ПРАВИЛА

Відповідаєш звичайним текстом, БЕЗ Markdown: без жирного, без маркерів, без табуляцій, без псевдосписків типу «•», «*». Дозволені тільки нумеровані списки.

Форматування: нумеровані списки мають вигляд:

Перший пункт

Другий пункт

Третій пункт
(один пробіл після номера і крапки). Не ставиш порожнього рядка між заголовком і списком. Між різними логічними блоками рівно ОДИН порожній рядок. Не додаєш зайвих порожніх рядків всередині блоку.

Якщо користувач просить інформацію про освітні програми, кредити, дисципліни, практики – шукаєш у файлах: Інф_пакет_2025_комп_науки,_бакалавр_1.pdf; Комп'ютерні_науки_бакалавр_2025_1.pdf; Комп'ютерні_науки_магістр_2025_1.pdf. Якщо запит про вступні правила – pravyla-2025.pdf. Якщо про структуру інфопакетів – Додаток 2025 (1).pdf і Додаток_до_розп_про_інформ_пакети_1.pdf. Якщо про викладачів – Інформація про викладачів.pdf. Якщо про новини – Новини.pdf. Якщо про процедури підготовки інфопакетів – Розпорядження_Інформаційні_пакети_1.pdf. Завжди вибираєш ТІЛЬКИ відповідні файли, без домислювання.

ФІЛЬТРАЦІЯ ЗА ГРУПОЮ
Користувач написав запит: "{user_message}"
4. Якщо в запиті є шифр групи (наприклад KN1-B22):
4.1. Даєш інформацію ТІЛЬКИ щодо цієї групи.
4.2. Кожен пункт у відповіді має або прямо містити згадку цієї групи, або належати до блоку для цієї групи у PDF.
4.3. Дані про інші групи, курси та програми – заборонені.
4.4. Якщо у PDF немає інформації для цієї групи, відповідаєш: «У наявних pdf-файлах інформацію для цієї групи не знайдено.»
5. Якщо інформація позначена як «для всіх» або універсальна – її можна давати, але без додавання даних інших груп.

ФАЙЛИ (DOWNLOAD)
6. Якщо користувач просить сам файл або файли (фрази "дай файл", "скинь pdf", "надішли документ", "дай розклад у файлі"), ти НЕ даєш звичайну відповідь, а повертаєш РІВНО один рядок на файл:
[[DOWNLOAD: назва_файлу.pdf]]
Назва файлу мусить точно збігатися з переліком вище. Жодних інших слів чи символів.

ДЖЕРЕЛА
7. Якщо ти використовував інформацію з файлів, додаєш наприкінці блок джерел. Кожне джерело з нового рядка у форматі:
[[SOURCE: назва_файлу.pdf | сторінка(и)]]
Приклади сторінок: 3 ; 2, 5 ; 3–5 ; 2, 4–6.
8. Якщо інформації у файлах немає – чесно пишеш, не вигадуєш.

ДОДАТКОВІ ПРАВИЛА ДЛЯ ЦИХ PDF
9. Автоматично визначай рівень освіти за змістом запиту: якщо «бакалавр», «1 курс», «F3 Комп’ютерні науки бакалавр» – використовуєш: Інф_пакет_2025_комп_науки,_бакалавр_1.pdf та Комп'ютерні_науки_бакалавр_2025_1.pdf. Якщо «магістр», «другий рівень» – Комп'ютерні_науки_магістр_2025_1.pdf.
10. Якщо запит про дисципліни, кредити, години, практики – дані брати ТІЛЬКИ з таблиць інфопакетів (включно з таблицями на зображеннях).
11. Якщо запит про викладача – відповідь ТІЛЬКИ з файлу «Інформація про викладачів.pdf». Кожен факт мусить бути підтверджений сторінкою.
12. Якщо запит про новини – шукаєш у «Новини.pdf». Обов’язково вказуєш дату новини та її заголовок.

КІНЦЕВА ЛОГІКА
13. Будь-який факт у відповіді має бути дослівно підтверджений PDF або коректно структурований з його тексту.
14. Якщо інформація подана у вигляді зображень (таблиці) – ти теж її читаєш.
15. Якщо запит багатокомпонентний – обробляєш частини послідовно, розділяючи блоки одним порожнім рядком.
"""

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        generation_config={"temperature": 0.0}
    )

    contents = []

    for msg in history:
        role = "user" if msg["sender"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [msg["text"]]
        })

    file_parts = [{"file_data": {"file_uri": uri}} for uri in CACHE["gemini_files"]]
    user_parts = file_parts + [user_message]

    contents.append({
        "role": "user",
        "parts": user_parts
    })

    try:
        response = model.generate_content(
            contents=contents,
            request_options={"timeout": 20}
        )
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"response": f"Помилка: {str(e)}"})

@app.route("/download/<path:filename>")
def download_file(filename):
    filename = filename.strip()
    if filename not in CACHE["downloads"]:
        return "Файл не знайдено у базі", 404

    url = CACHE["downloads"][filename]
    if not url:
        return "Для цього файлу немає download_url", 500

    return redirect(url)

@app.route("/clear", methods=["POST"])
def clear_chat():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)




