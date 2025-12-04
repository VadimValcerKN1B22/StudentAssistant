import os
import io
import time
from threading import Thread
from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

# --- PATH CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

# --- FLASK APP ---
app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)

# --- ENV VARS ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_FOLDER_NAME = os.getenv("TARGET_FOLDER_NAME", "StudentAssistantData")

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')

genai.configure(api_key=GEMINI_API_KEY)

# --- CACHE STORAGE ---
CACHE = {
    "gemini_files": [],
    "file_names": [],
    "file_bodies": {}
}

# -------------------------
#   GOOGLE DRIVE LOGIN
# -------------------------
def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print("❌ credentials.json не знайдено!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# -------------------------
#       SYNC FUNCTION
# -------------------------
def sync_data():
    print("🔄 Починаю завантаження файлів...")

    service = get_drive_service()
    if not service:
        print("❌ Сервіс Google Drive не створено!")
        return False

    results = service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{TARGET_FOLDER_NAME}' and trashed=false",
        fields="files(id)"
    ).execute()

    folders = results.get('files', [])
    if not folders:
        print("❌ Папку не знайдено!")
        return False

    folder_id = folders[0]['id']

    results_files = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
        fields="files(id, name)"
    ).execute()

    pdfs = results_files.get('files', [])

    CACHE["gemini_files"] = []
    CACHE["file_names"] = []
    CACHE["file_bodies"] = {}

    for pdf in pdfs:
        print(f"📥 Скачування: {pdf['name']}...")

        request = service.files().get_media(fileId=pdf['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        file_bytes = fh.getvalue()

        CACHE["file_names"].append(pdf['name'])
        CACHE["file_bodies"][pdf['name']] = file_bytes

        temp_path = f"temp_{pdf['name']}"
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        try:
            g_file = genai.upload_file(path=temp_path, display_name=pdf['name'])
            CACHE["gemini_files"].append(g_file)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    print("⏳ Очікування обробки ШІ...")
    for f in CACHE["gemini_files"]:
        while True:
            remote = genai.get_file(f.name)
            if remote.state.name in ["ACTIVE", "FAILED"]:
                break
            time.sleep(0.5)

    print(f"✅ Готово! Завантажено {len(CACHE['file_names'])} файлів.")
    return True

# -------------------------
#   BACKGROUND SYNC THREAD
# -------------------------
def run_background_sync():
    with app.app_context():
        try:
            sync_data()
        except Exception as e:
            print("❌ Помилка синхронізації:", e)

@app.before_serving
def start_background_sync():
    print("🚀 Запускаю асинхронну синхронізацію файлів...")
    Thread(target=run_background_sync, daemon=True).start()

# -------------------------
#        ROUTES
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    history = request.json.get("history", [])

    if not CACHE["gemini_files"]:
        return jsonify({"response": "Система завантажується. Спробуйте за 5–30 секунд."})

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

        chat_session = [{"role": "user", "parts": CACHE["gemini_files"] + ["Start session."]}]
        chat_session.append({"role": "model", "parts": ["Ready."]})

        for msg in history:
            role = "user" if msg['sender'] == 'user' else "model"
            chat_session.append({"role": role, "parts": [msg['text']]})

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

# --- LOCAL DEV ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)

