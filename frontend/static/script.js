const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const loadingIndicator = document.getElementById('loading-indicator');
const scrollBtn = document.getElementById("scroll-down-btn");
const input = document.getElementById("user-input");
const inputDiv = document.querySelector(".input-div");
const footer = document.querySelector('footer');

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
        contentDiv.innerHTML = linkify(text);
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

async function sendMessage() {
    const text = userInput.innerText.trim();
    if (!text) return;

    addMessage(text, 'user');
    userInput.innerHTML = '';
    userInput.style.height = 'auto';

    loadingIndicator.classList.remove('hidden');
    updateSendButtonState();
    chatBox.appendChild(loadingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
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

        loadingIndicator.classList.add('hidden');
        updateSendButtonState();

        if (cleanText.length > 0) {
            addMessage(cleanText, 'bot', true);
        }

    } catch (error) {
        loadingIndicator.classList.add('hidden');
        addMessage("Помилка з'єднання. Перевірте консоль.", 'bot');
        console.error(error);
    }
}

sendBtn.addEventListener('click', sendMessage);

document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !sendBtn.classList.contains("disabled")) {
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
updateClearButtonState();

function updateSendButtonState() {
    const textEmpty = userInput.innerText.trim().length === 0;
    const isLoading = !loadingIndicator.classList.contains("hidden");

    sendBtn.classList.toggle("disabled", textEmpty || isLoading);
}

userInput.addEventListener("input", updateSendButtonState);
const observerSend = new MutationObserver(updateSendButtonState);
observerSend.observe(loadingIndicator, { attributes: true });
updateSendButtonState();

function linkify(text) {
    const urlRegex = /(https?:\/\/[^\s<]+)/g;
    return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

userInput.spellcheck = false;
