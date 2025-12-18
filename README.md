<div align="center">

<img src="frontend/static/assets/logo.png" alt="StudentAssistant Logo" width="120" />

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
