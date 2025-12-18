# StudentAssistant

### Веб-асистент для студентів: відповідає на питання з документів кафедри (PDF) через Groq LLM

<br/>

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20App-black)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![LlamaParse](https://img.shields.io/badge/LlamaParse-PDF%20Parsing-purple)
![Google Drive](https://img.shields.io/badge/Google%20Drive-API-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

## 📌 Про проєкт

StudentAssistant — це веб-застосунок на Flask, який:
- автоматично завантажує всі PDF з заданої папки Google Drive,
- витягує текст через LlamaParse,
- віддає відповідь користувачу через Groq (llama-3.3-70b-versatile),
- відповідає **тільки** на основі контексту з документів (без “фантазій” ззовні).

---

## 🚀 Основні можливості

- ✅ Чат-інтерфейс у браузері
- ✅ Автопарсинг PDF (Google Drive → LlamaParse → текст)
- ✅ Відповіді на основі контексту документів
- ✅ Формат новин (1 новина = 3 рядки: текст / дата / посилання)
- ✅ Ротація API-ключів (карусель) для стабільності та лімітів
- ✅ Клікабельні посилання у відповідях

---

## 🧩 Архітектура проєкту

```text
STUDENTASSISTANT/
├─ backend/
│  ├─ app.py
│  ├─ credentials.json        (НЕ пушити в GitHub)
│  ├─ token.json              (НЕ пушити в GitHub)
│  └─ .env                    (НЕ пушити в GitHub)
│
├─ frontend/
│  ├─ static/
│  │  ├─ assets/
│  │  │  └─ logo.png
│  │  ├─ script.js
│  │  └─ style.css
│  └─ templates/
│     └─ index.html
│
├─ requirements.txt
└─ README.md
````

---

## ⚙️ Встановлення та запуск

### 1) Клон / завантаження

Якщо без git — просто скачай ZIP репозиторію з GitHub і розпакуй.

### 2) Створи virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Встанови залежності

```bash
pip install -r requirements.txt
```

### 4) Налаштуй Google OAuth (обовʼязково)

У папку `backend/` поклади файл:

* `credentials.json`

Після першого запуску зʼявиться:

* `token.json` (його НЕ пушити)

### 5) Створи `.env` у `backend/`

`backend/.env`:

```env
TARGET_FOLDER_NAME=Назва_папки_на_Google_Drive

GROQ_API_KEY_1=...
GROQ_API_KEY_2=...
GROQ_API_KEY_3=...
GROQ_API_KEY_4=...
GROQ_API_KEY_5=...
GROQ_API_KEY_6=...
GROQ_API_KEY_7=...
GROQ_API_KEY_8=...
GROQ_API_KEY_9=...
GROQ_API_KEY_10=...

LLAMA_CLOUD_API_KEY_1=...
LLAMA_CLOUD_API_KEY_2=...
LLAMA_CLOUD_API_KEY_3=...
LLAMA_CLOUD_API_KEY_4=...
LLAMA_CLOUD_API_KEY_5=...
```

### 6) Запуск

Запускай з папки `backend/`:

```bash
python app.py
```

Відкрий у браузері:

```text
http://127.0.0.1:5000
```

---

## 🔑 Де взяти ключі

### Groq API Keys

* [https://console.groq.com/keys](https://console.groq.com/keys)

### Llama Cloud API Keys (LlamaParse)

* [https://cloud.llamaindex.ai/api-keys](https://cloud.llamaindex.ai/api-keys)

---

## 🛡️ Важливо про безпеку

НЕ додавай у GitHub:

* `backend/.env`
* `backend/credentials.json`
* `backend/token.json`
* `venv/`

Рекомендовано додати `.gitignore`:

```gitignore
.env
credentials.json
token.json
venv/
__pycache__/
*.pyc
```

---

## 🧪 Як користуватись

1. Відкрий сайт
2. Напиши питання (наприклад: “Які правила вступу?” або “Які новини за вересень?”)
3. Отримаєш відповідь, сформовану на основі PDF документів

---

## 🧰 Технологічний стек

| Категорія   | Технології                     |
| ----------- | ------------------------------ |
| Backend     | Python, Flask                  |
| Frontend    | HTML, CSS, JavaScript          |
| LLM         | Groq (llama-3.3-70b-versatile) |
| PDF Parsing | LlamaParse (Llama Cloud)       |
| Джерело PDF | Google Drive API (OAuth)       |

---

## 🤝 Як долучитись (Contributing)

1. Зроби Fork репозиторію
2. Створи нову гілку
3. Внеси зміни
4. Відкрий Pull Request

---

## 📄 Ліцензія

---

<div align="center">

Made with ❤️ in Ukraine 🇺🇦

</div>


