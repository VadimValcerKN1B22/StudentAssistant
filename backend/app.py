import os
import io
import tempfile
import itertools
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from llama_parse import LlamaParse
from groq import Groq

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_FOLDER_NAME = os.getenv("TARGET_FOLDER_NAME")

GROQ_KEYS = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 11)]
GROQ_KEYS = [k for k in GROQ_KEYS if k]
GROQ_CAROUSEL = itertools.cycle(GROQ_KEYS)

LLAMA_KEYS = [os.getenv(f"LLAMA_CLOUD_API_KEY_{i}") for i in range(1, 6)]
LLAMA_KEYS = [k for k in LLAMA_KEYS if k]
LLAMA_CAROUSEL = itertools.cycle(LLAMA_KEYS)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static"),
    static_url_path="/static"
)

CONTEXT_TEXT = ""

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)

def download_pdf(service, file_id):
    req = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def _is_retryable_error(e: Exception) -> bool:
    s = str(e).lower()
    return any(x in s for x in [
        "rate", "limit", "quota", "429",
        "timeout", "overloaded",
        "unavailable", "503", "502", "504"
    ])

def load_and_parse_files():
    global CONTEXT_TEXT
    if CONTEXT_TEXT:
        return

    service = get_drive_service()

    folder = service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{TARGET_FOLDER_NAME}' and trashed=false",
        fields="files(id)"
    ).execute()["files"]

    if not folder:
        return

    folder_id = folder[0]["id"]

    files = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
        fields="files(id, name)"
    ).execute()["files"]

    texts = []
    last_err = None

    for _ in range(max(1, len(LLAMA_KEYS))):
        os.environ["LLAMA_CLOUD_API_KEY"] = next(LLAMA_CAROUSEL)
        try:
            parser = LlamaParse(result_type="text", language="uk")
            for f in files:
                pdf_bytes = download_pdf(service, f["id"])
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_bytes.getvalue())
                    path = tmp.name
                documents = parser.load_data(path)
                for doc in documents:
                    texts.append(doc.text)
                os.remove(path)
            CONTEXT_TEXT = "\n\n".join(texts)
            return
        except Exception as e:
            last_err = e
            if not _is_retryable_error(e):
                break

    raise last_err if last_err else RuntimeError("Помилка парсингу PDF")

def get_system_prompt():
    return f"""
Ти — StudentAssistant.
Працюєш ТІЛЬКИ українською мовою.

У тебе є ПОВНИЙ текст усіх файлів.
Ти НЕ маєш використовувати знання поза цим текстом.

ПРАВИЛА:
1. Якщо інформації немає — так і скажи.
2. Пиши чітко, без води.
3. Без markdown.
4. Нумерація тільки 1. 2. 3.
5. Використовуй ТІЛЬКИ коротке тире "-".

ВАЖЛИВО:
- НЕ ПОКАЗУЙ процес міркування, перевірок або відбору.
- НЕ ПИШИ фрази типу "відповідає / не відповідає".
- НЕ КОМЕНТУЙ, чому щось не підійшло.
- ДАВАЙ ЛИШЕ КІНЦЕВУ ВІДПОВІДЬ ДЛЯ КОРИСТУВАЧА.
- ЯКЩО ПОТРІБНА ФІЛЬТРАЦІЯ — ВИВОДЬ ТІЛЬКИ ТЕ, ЩО ПІДХОДИТЬ.

НОВИНИ:
- ОДНА новина = ТРИ РЯДКИ.
- ПЕРШИЙ рядок: заголовок і короткий текст в ОДНОМУ рядку.
- ДРУГИЙ рядок: "Дата: ".
- ТРЕТІЙ рядок: "Посилання: " і ПРЯМИЙ URL.
- ЯКЩО ПОСИЛАНЬ КІЛЬКА — КОЖНЕ З НОВОГО РЯДКА.
- НЕ ВИКОРИСТОВУЙ дужки, markdown або HTML для посилань.

ДАТИ:
- ДАТИ визначай ТІЛЬКИ з явно вказаних дат у тексті.
- ЯКЩО місяць або дата не вказані чітко — вважай, що інформації немає.

КОНТЕКСТ:
{CONTEXT_TEXT}
""".strip()

def groq_complete_with_fallback(messages, model="llama-3.3-70b-versatile", temperature=0.3, max_tokens=1200):
    last_err = None
    for _ in range(max(1, len(GROQ_KEYS))):
        try:
            client = Groq(api_key=next(GROQ_CAROUSEL))
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_err = e
            if not _is_retryable_error(e):
                break
    raise last_err if last_err else RuntimeError("Помилка Groq")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    message = (request.json or {}).get("message", "").strip()
    if not message:
        return jsonify({"response": "Введіть запит."})

    try:
        text = groq_complete_with_fallback([
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": message}
        ])
        return jsonify({"response": text})
    except Exception as e:
        return jsonify({"response": f"Помилка запиту до моделі: {str(e)}"})

if __name__ == "__main__":
    load_and_parse_files()
    app.run(debug=True, port=5000, use_reloader=False)
