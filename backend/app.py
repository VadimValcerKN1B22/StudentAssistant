import os
import json
from flask import Flask, render_template, request, jsonify
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
TARGET_FOLDER_NAME = os.getenv("TARGET_FOLDER_NAME", "StudentAssistantData")

genai.configure(api_key=GEMINI_API_KEY)

CACHE = {
    "gemini_files": [],
    "file_names": []
}

def load_indexed_files():
    if not os.path.exists(INDEXED_PATH):
        print("indexed_files.json не знайдено")
        return

    with open(INDEXED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    CACHE["gemini_files"] = [item["file_uri"] for item in data]
    CACHE["file_names"] = [item["name"] for item in data]
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

        for uri in CACHE["gemini_files"]:
            contents.append({"file_data": {"file_uri": uri}})

        contents.append(user_message)

        response = model.generate_content(
            contents=contents,
            request_options={"timeout": 20}
        )

        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"response": f"Помилка: {str(e)}"})

@app.route("/clear", methods=["POST"])
def clear_chat():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)



