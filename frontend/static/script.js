const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const loadingIndicator = document.getElementById('loading-indicator');
const scrollBtn = document.getElementById("scroll-down-btn");
const input = document.getElementById("user-input");
const inputDiv = document.querySelector(".input-div");
const footer = document.querySelector('footer');

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
    updateScrollButton();
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
                 ${f}
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

    let block = document.createElement("div");
    block.classList.add("source-block");

    const titleSources = document.createElement("div");
    titleSources.className = "sf-title";
    titleSources.innerHTML = `📄 <b>Джерела:</b>`;
    block.appendChild(titleSources);

    sources.forEach(s => {
        const row = document.createElement("div");
        row.className = "sf-row";

        const dot = document.createElement("span");
        dot.className = "sf-dot";
        dot.textContent = "•";

        const text = document.createElement("span");
        text.className = "sf-text";
        text.textContent = `${s.cleanName}${formatPages(s.pages)}`;

        row.appendChild(dot);
        row.appendChild(text);
        block.appendChild(row);
    });

    const titleFiles = document.createElement("div");
    titleFiles.className = "sf-title";
    titleFiles.style.marginTop = "10px";
    titleFiles.innerHTML = `⬇️ <b>Файли:</b>`;
    block.appendChild(titleFiles);

    downloads.forEach(f => {
        const row = document.createElement("div");
        row.className = "sf-row";

        const dot = document.createElement("span");
        dot.className = "sf-dot";
        dot.textContent = "•";

        const link = document.createElement("a");
        link.className = "sf-file";
        link.href = `/download/${f}`;
        link.textContent = f;

        row.appendChild(dot);
        row.appendChild(link);
        block.appendChild(row);
    });

    lastContent.appendChild(block);
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

const scrollDownBtn = document.getElementById("scroll-down-btn");

function updateScrollButton() {
    const nearBottom =
        chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 140;

    if (nearBottom) {
        scrollDownBtn.classList.remove("show");
    } else {
        scrollDownBtn.classList.add("show");
    }
}

chatBox.addEventListener("scroll", updateScrollButton);

scrollDownBtn.addEventListener("click", () => {
    chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
});

function updateScrollBtnPosition() {
    const footerHeight = footer.offsetHeight;  

    let offset = 20; 

    if (window.innerWidth < 480) {
        offset = 15;       
    } else if (window.innerWidth < 768) {
        offset = 20;       
    }
    
    scrollBtn.style.bottom = (footerHeight + offset) + "px";
}

window.addEventListener("resize", updateScrollBtnPosition);
userInput.addEventListener("input", updateScrollBtnPosition); 
chatBox.addEventListener("scroll", updateScrollBtnPosition);
updateScrollBtnPosition();

function updateClearButtonState() {
    const clearBtn = document.getElementById("clear-btn");

    const messages = [...document.querySelectorAll(".message")]
        .filter(m => !m.classList.contains("system-message"));

    clearBtn.classList.toggle("disabled", messages.length === 0);
}

document.getElementById("clear-btn").addEventListener("click", () => {
    const main = document.querySelector("main");
    const systemMessage = document.querySelector(".system-message");
    main.innerHTML = "";
    if (systemMessage) main.appendChild(systemMessage);
    updateClearButtonState();
});

const observer = new MutationObserver(updateClearButtonState);
observer.observe(document.querySelector("main"), { childList: true });



