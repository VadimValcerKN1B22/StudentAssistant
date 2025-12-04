const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const loadingIndicator = document.getElementById('loading-indicator');

let history = [];

function addMessage(text, sender, isHtml = false) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');

    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('avatar');
    const img = document.createElement('img');
    img.src = sender === 'user'
        ? "https://cdn-icons-png.flaticon.com/512/1946/1946429.png"
        : "/static/assets/logo.png";
    avatarDiv.appendChild(img);

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('content');

    if (isHtml) {
        contentDiv.innerHTML = text;
    } else {
        contentDiv.textContent = text;
    }

    if (sender === 'user') {
        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(avatarDiv);
    } else {
        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
    }

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addFilesMessage(files) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', 'bot-message');

    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('avatar');
    const img = document.createElement('img');
    img.src = "/static/assets/logo.png";
    avatarDiv.appendChild(img);

    const fileDiv = document.createElement('div');
    fileDiv.classList.add('file-container');

    const title = files.length === 1
        ? "Ось потрібний вам файл:"
        : "Ось потрібні вам файли:";

    let html = `<div class="file-label">${title}</div>`;

    files.forEach(f => {
    html += `
        <div class="file-download-row">
            <span class="file-emoji">➡️</span>
            <a href="/download/${f}" class="file-download">
                Скачати ${f}
            </a>
        </div>
    `;
});

    fileDiv.innerHTML = html;

    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(fileDiv);

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function formatPages(pagesArr) {
    if (!pagesArr || pagesArr.length === 0) return "";
    const unique = [...new Set(pagesArr)];
    const label = unique.length > 1 ? "сторінки" : "сторінка";
    return ` (${label} ${unique.join(", ")})`;
}

function appendSourcesAndFilesToLastBotMessage(sources, downloads) {
    const lastContent = chatBox.querySelector('.bot-message:last-child .content');
    if (!lastContent) return;

    let html = "";

    html += `<div class="source-block">`;

    html += `<div>📄 <b>${sources.length > 1 ? "Джерела:" : "Джерело:"}</b></div>`;

    sources.forEach(s => {
        html += `• ${s.cleanName}${formatPages(s.pages)}<br>`;
    });

    html += `<div style="margin-top:4px;">⬇️ <b>${downloads.length > 1 ? "Файли:" : "Файл:"}</b></div>`;
    downloads.forEach(f => {
        html += `• <a href="/download/${f}" class="file-download">Скачати ${f}</a><br>`;
    });

    html += `</div>`;

    lastContent.innerHTML += html;
}

async function sendMessage() {
    const text = userInput.innerText.trim();
    if (!text) return;

    addMessage(text, 'user');
    userInput.innerHTML = '';
    userInput.style.height = 'auto';

    loadingIndicator.classList.remove('hidden');
    chatBox.appendChild(loadingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, history: history })
        });

        const data = await response.json();
        let cleanText = data.response;

cleanText = cleanText.replace(
    /(^|\n)1\. ([^\n]+)(\n(?!2\. ).+)?(?=\n\n|$)/g,
    (match, start, item, extra) => {
        if (!/^\s*2\./m.test(extra || "")) {
            return `${start}${item}${extra || ""}`;
        }
        return match;
    }
);
        const downloadMatches = [...cleanText.matchAll(/\[\[DOWNLOAD:\s*(.*?)\]\]/g)];
        let downloads = downloadMatches.map(m => m[1].trim());
        downloads = [...new Set(downloads)];

        const sourceMatches = [...cleanText.matchAll(/\[\[SOURCE:\s*(.*?)\]\]/g)];
        const sourceMap = new Map();

        sourceMatches.forEach(match => {
            let part = match[1].trim();
            let [file, pagesRaw] = part.split('|').map(s => s.trim());
            const cleanName = file.replace(/\.pdf$/i, '');

            let nums = [];
            if (pagesRaw) {
                const found = pagesRaw.match(/\d+/g);
                if (found) nums = found.map(x => x.trim());
            }

            if (!sourceMap.has(file)) {
                sourceMap.set(file, {
                    file,
                    cleanName,
                    pages: nums
                });
            } else {
                const existing = sourceMap.get(file);
                existing.pages = [...new Set([...existing.pages, ...nums])];
            }
        });

        const sources = Array.from(sourceMap.values());

        cleanText = cleanText
    .replace(/\[\[DOWNLOAD:.*?\]\]/g, '')
    .replace(/\[\[SOURCE:.*?\]\]/g, '')
    .trim();

        loadingIndicator.classList.add('hidden');

        if (cleanText.length > 0) {
            addMessage(cleanText, 'bot', true);
        }

        if (sources.length > 0) {
            if (downloads.length === 0) {
                downloads = sources.map(s => s.file);
            }
            downloads = [...new Set(downloads)];

            appendSourcesAndFilesToLastBotMessage(sources, downloads);
        } else if (cleanText.length === 0 && downloads.length > 0) {
            addFilesMessage(downloads);
        }

        history.push({ sender: 'user', text });
        history.push({ sender: 'bot', text: data.response });

    } catch (error) {
        loadingIndicator.classList.add('hidden');
        addMessage("Помилка з'єднання. Перевірте консоль.", 'bot');
        console.error(error);
    }
}

sendBtn.addEventListener('click', sendMessage);

document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

clearBtn.addEventListener('click', () => location.reload());

userInput.addEventListener("input", () => {
    if (userInput.innerText.trim() === "") {
        userInput.innerHTML = "";
    }
});

userInput.addEventListener('paste', (e) => {
    e.preventDefault();

    const text = (e.clipboardData || window.clipboardData).getData('text/plain') || '';

    if (document.queryCommandSupported('insertText')) {
        document.execCommand('insertText', false, text);
    } else {
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        const range = selection.getRangeAt(0);
        range.deleteContents();
        range.insertNode(document.createTextNode(text));
        range.collapse(false);
    }
});

document.addEventListener("mousedown", (e) => {
    const isChatText = e.target.closest(".message .content");
    const isInput = e.target.closest("#user-input");

    if (!isChatText && !isInput) {
        window.getSelection()?.removeAllRanges();
    }
});