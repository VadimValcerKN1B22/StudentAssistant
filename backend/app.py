import os
import json
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # корінь проекту
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
INDEXED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indexed_files.json")

load_dotenv()  # читає .env з кореня проекту (ти так і хочеш)

# --- FLASK APP ---
app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)

# --- GEMINI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("ENV GEMINI_API_KEY не заданий")

genai.configure(api_key=GEMINI_API_KEY)

# --- CACHE ---
CACHE = {
    "gemini_files": [],   # список file_uri
    "file_names": []      # відповідні імена файлів
}


def load_indexed_files():
    if not os.path.exists(INDEXED_PATH):
        print("indexed_files.json не знайдено")
        return

    with open(INDEXED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # підтримуємо і формат-список, і старий формат-словник
    if isinstance(data, dict):
        items = [{"name": name, "file_uri": uri} for name, uri in data.items()]
    else:
        items = data

    CACHE["gemini_files"] = [item["file_uri"] for item in items]
    CACHE["file_names"] = [item["name"] for item in items]

    print(f"Завантажено з indexed_files.json: {len(CACHE['file_names'])} файлів")


load_indexed_files()


# --- ROUTES ---

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(force=True) or {}
    user_message = (payload.get("message") or "").strip()
    history = payload.get("history", [])

    if not user_message:
        return jsonify({"response": "Ви нічого не написали."})

    if not CACHE["gemini_files"]:
        return jsonify({"response": "Система ще не має жодного проіндексованого файлу. Зверніться до адміністратора."})

    files_str = ", ".join(CACHE["file_names"])

    system_prompt = f"""
Ти – StudentAssistant. Працюєш ТІЛЬКИ українською мовою.

Твоя база знань складається ТІЛЬКИ з цих PDF-файлів:
{files_str}

Інших джерел інформації в тебе немає.

ЗАГАЛЬНІ ПРАВИЛА
1. Відповідаєш звичайним текстом, БЕЗ Markdown:
   – без **жирного**, 
   – без маркерів типу *, •, -, 
   – без табуляцій або псевдо-списків зі зірочками.
2. Форматуєш акуратно:
   – нумеровані списки мають вигляд:
     1. Перший пункт
     2. Другий пункт
     3. Третій пункт
     (один пробіл після номера і крапки, без подвійних пробілів);
   – НЕ ставиш порожнього рядка між заголовком і першим пунктом списку;
   – між різними логічними блоками (екзамени / курсові / інша частина) – рівно ОДИН порожній рядок;
   – не додаєш зайві пусті рядки всередині блоку.

ФІЛЬТРАЦІЯ ЗА ГРУПОЮ
Користувач написав такий запит:
"{user_message}"

3. Якщо в запиті явно згадується шифр групи (наприклад "KN1-B22"):
   3.1. Ти МАЄШ дати розклад ТІЛЬКИ для цієї групи.
   3.2. Кожен пункт, який ти додаєш у відповідь (екзамен, курсова робота тощо),
        повинен однозначно належати саме до цієї групи:
        – або це рядок / абзац, де явно згадується ця група;
        – або це пункт, який знаходиться всередині блоку з заголовком для цієї групи
          (типу "Для групи KN1-B22 …").
   3.3. Якщо пункт стосується іншої групи, іншої спеціальності або блоку з іншим заголовком –
        ТИ НЕ МАЄШ ПРАВА його додавати у відповідь.
   3.4. Якщо в файлах немає жодної інформації саме для запитаної групи –
        чесно скажи, що розклад для цієї групи в наявних файлах не знайдено, і нічого не вигадуй.

4. Якщо інформація в файлі явно позначена як "для всіх груп" або не прив’язана до конкретної групи,
   її можна використовувати як спільну, але не додавай при цьому специфічні пункти інших груп.

ФАЙЛИ (DOWNLOAD)
5. Якщо користувач просить саме файл або файли (формулювання типу:
   "дай файл/файли", "скинь файл/файли", "надішли pdf/pdfи", "дай розклад у файлі/файлах" тощо),
   то ти НЕ пишеш звичайну відповідь, а повертаєш РІВНО один рядок такого вигляду, для кожного файлу:
   [[DOWNLOAD: назва_файлу.pdf]]
   – без додаткового тексту до чи після.
   Назва_файлу.pdf ОБОВ’ЯЗКОВО повинна точно збігатися з однією з назв із списку вище.

ДЖЕРЕЛА
6. Якщо ти використовував інформацію з pdf-файлів, додай блок джерел наприкінці відповіді.
   Кожне джерело з нового рядка у форматі:
   [[SOURCE: назва_файлу.pdf | сторінка(и)]]
   Приклади сторінок: "3", "2, 5", "3–5", "2, 4–6".
   Назви файлів у тегах SOURCE повинні ТОЧНО збігатися з назвами із списку:
   {files_str}

7. Якщо відповісти на питання на основі цих файлів неможливо,
   чесно скажи, що в наявних pdf-файлах такої інформації немає, і нічого не вигадуй.
"""

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.0},
            system_instruction=system_prompt
        )

        contents = []

        # 1. ІСТОРІЯ ЧАТУ (памʼять)
        for msg in history:
            text = (msg.get("text") or "").strip()
            if not text:
                continue

            role = "user" if msg.get("sender") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [text]  # ВАЖЛИВО: parts, а не text
            })

        # 2. ПОТОЧНЕ ПОВІДОМЛЕННЯ + ФАЙЛИ
        file_parts = [{"file_data": {"file_uri": uri}} for uri in CACHE["gemini_files"]]

        contents.append({
            "role": "user",
            "parts": file_parts + [user_message]
        })

        response = model.generate_content(
            contents=contents,
            request_options={"timeout": 20}
        )

        return jsonify({"response": response.text})

    except Exception as e:
        print("Gemini error:", e)
        return jsonify({"response": f"Помилка: {str(e)}"})

@app.route("/clear", methods=["POST"])
def clear_chat():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
