/**
 * @file chat-embedded.js
 * Embedded chat widget — działa niezależnie od głównego chat.js.
 * Reużywa ten sam singleton WebSocket (websocket-manager.js).
 *
 * Użycie w template:
 *   <div class="embedded-chat" data-room-id="42" data-csrf="{{ csrf_token }}"></div>
 *   <script type="module" src="{% static 'chat/js/chat-embedded.js' %}"></script>
 */

import { getSharedWebSocket } from './websocket-manager.js';

/** Formatuje timestamp HH:MM */
function formatTime(ts) {
    const d = new Date(ts);
    return d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
}

/** Formatuje datę jako d.m.YYYY */
function formatDate(ts) {
    const d = new Date(ts);
    return `${d.getDate()}.${d.getMonth() + 1}.${d.getFullYear()}`;
}

/** Escapuje HTML żeby zapobiec XSS */
function escapeHtml(s) {
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/** Zamienia URL-e na klikalne linki */
function linkify(text) {
    const escaped = escapeHtml(text);
    return escaped.replace(
        /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)/g,
        (url) => `<a href="${url}" target="_blank" rel="noopener">${url}</a>`
    );
}

/**
 * Inicjalizuje embedded chat dla podanego elementu DOM.
 * @param {HTMLElement} container  - div.embedded-chat z data-room-id i data-csrf
 */
async function initEmbeddedChat(container) {
    const roomId  = parseInt(container.dataset.roomId, 10);
    const csrf    = container.dataset.csrf;
    if (!roomId) return;

    // ── 1. Zbuduj HTML widgetu ────────────────────────────────────────────────
    container.innerHTML = `
        <div class="ec-wrapper">
            <div class="ec-messages" id="ec-messages-${roomId}">
                <div class="ec-loading">Ładowanie…</div>
            </div>
            <form class="ec-form" id="ec-form-${roomId}" autocomplete="off">
                <textarea class="ec-input" id="ec-input-${roomId}"
                    rows="1" placeholder="Napisz wiadomość…" enterkeyhint="send"></textarea>
                <button class="ec-send" type="submit" title="Wyślij">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </form>
        </div>
    `;

    const messagesEl = container.querySelector(`#ec-messages-${roomId}`);
    const form       = container.querySelector(`#ec-form-${roomId}`);
    const input      = container.querySelector(`#ec-input-${roomId}`);

    // ── 2. Helpers DOM ────────────────────────────────────────────────────────
    let lastDateBanner = null;

    /** Zwraca true jeśli wiadomość to auto-generated system link (np. "Pokój dyskusyjny dla zadania: https://...") */
    function isSystemLink(message) {
        // Wiadomość zawiera dokładnie jeden URL i nic poza krótkim prefiksem tekstowym
        return /^[^:]{0,80}:\s*https?:\/\/\S+$/.test(message.trim());
    }

    function appendMessage({ message_id, username, message, timestamp, latest_timestamp, own }) {
        // Ukryj auto-generowane system linki (np. inicjalna wiadomość z linkiem do zadania)
        if (isSystemLink(message)) return;

        const original_ts = timestamp;
        const latest_ts   = latest_timestamp ?? timestamp;
        // Separator daty jeśli nowy dzień
        const dateStr = formatDate(original_ts);
        if (dateStr !== lastDateBanner) {
            lastDateBanner = dateStr;
            const sep = document.createElement('div');
            sep.className = 'ec-date-sep';
            sep.textContent = dateStr;
            messagesEl.appendChild(sep);
        }

        const div = document.createElement('div');
        div.className = `ec-msg${own ? ' ec-msg--own' : ''}`;
        div.dataset.messageId = message_id;
        div.innerHTML = `
            <span class="ec-msg-author">${escapeHtml(username)}</span>
            <span class="ec-msg-text">${linkify(message)}</span>
            <span class="ec-msg-time">${formatTime(latest_ts)}</span>
        `;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function updateMessage({ message_id, message, latest_timestamp }) {
        const latest_ts = latest_timestamp;
        const div = messagesEl.querySelector(`[data-message-id="${message_id}"]`);
        if (!div) return;
        const textEl = div.querySelector('.ec-msg-text');
        const timeEl = div.querySelector('.ec-msg-time');
        if (textEl) textEl.innerHTML = linkify(message);
        if (timeEl) timeEl.textContent = formatTime(latest_ts);
    }

    function setLoading(text) {
        const el = messagesEl.querySelector('.ec-loading');
        if (el) el.textContent = text;
    }

    // ── 3. WebSocket ──────────────────────────────────────────────────────────
    const ws = getSharedWebSocket();
    let joined = false;

    // Bufor wiadomości które przychodą zanim joinRoom() się zakończy
    let pendingMessages = [];
    let joinDone = false;

    function joinRoom() {
        if (joined) return;
        ws.sendJsonAsync({ command: 'join', room_id: roomId })
            .then(() => {
                joined = true;
                // Wiadomości historyczne ({messages:[...]}) przychodzą jako osobny pakiet
                // bez __TRACE_ID — trafiają do onMessage() asynchronicznie po rozwiązaniu
                // tej Promise. Odkładamy finalizację na kolejny tick event loop, żeby
                // onMessage() zdążył przetworzyć historię przed sprawdzeniem czy jest pusta.
                setTimeout(() => {
                    joinDone = true;
                    messagesEl.innerHTML = '';
                    for (const msg of pendingMessages) {
                        appendMessage(msg);
                    }
                    pendingMessages = [];
                    if (messagesEl.children.length === 0) {
                        messagesEl.innerHTML = '<div class="ec-empty">Brak wiadomości. Napisz pierwszy!</div>';
                    }
                }, 0);
            })
            .catch(err => {
                setLoading('Brak dostępu do tego czatu.');
                console.error('embedded chat join error:', err);
            });
    }

    // Handler dla broadcast-ów przychodzących z serwera (bez TRACE_ID)
    function onMessage(data) {
        if (data.messages) {
            for (const msg of data.messages) {
                // Pomiń wiadomości z innych pokojów
                if (msg.room_id && msg.room_id !== roomId) continue;
                if (!joinDone) {
                    // Historia przychodzi przed rozwiązaniem Promise — buforuj
                    pendingMessages.push(msg);
                } else {
                    appendMessage(msg);
                }
            }
        }
        if (data.edit) {
            updateMessage(data.edit);
        }
    }

    ws.addMessageHandler(onMessage);

    // Dołącz natychmiast jeśli WS już połączony, lub po połączeniu
    if (ws.socket.readyState === WebSocket.OPEN) {
        joinRoom();
    } else {
        // setOnConnect nadpisałoby istniejący handler — użyj jednorazowego listenera
        const originalOpen = ws.socket.onopen;
        ws.socket.onopen = function(e) {
            if (originalOpen) originalOpen.call(this, e);
            joinRoom();
        };
    }

    // ── 4. Wysyłanie wiadomości ───────────────────────────────────────────────
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text || !joined) return;
        ws.sendJson({
            command: 'send',
            room_id: roomId,
            message: text,
            is_anonymous: false,
            attachments: {},
        });
        input.value = '';
        input.style.height = 'auto';
    });

    // Enter wysyła (Shift+Enter = nowa linia)
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.requestSubmit();
        }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    // ── 5. Cleanup przy nawigacji ─────────────────────────────────────────────
    window.addEventListener('beforeunload', () => {
        ws.removeMessageHandler(onMessage);
        if (joined) {
            ws.sendJson({ command: 'leave', room_id: roomId });
        }
    });
}

// ── Bootstrap: inicjalizuj wszystkie widgety na stronie ──────────────────────
document.addEventListener('DOMContentLoaded', () => {
    for (const el of document.querySelectorAll('.embedded-chat[data-room-id]')) {
        initEmbeddedChat(el);
    }
});
