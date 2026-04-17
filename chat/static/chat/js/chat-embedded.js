/**
 * @file chat-embedded.js
 * Embedded chat widget — reużywa Message template i CSS z głównego czatu.
 *
 * Użycie w template:
 *   <div class="embedded-chat" data-room-id="42" data-csrf="{{ csrf_token }}"></div>
 *   <script type="module" src="{% static 'chat/js/chat-embedded.js' %}"></script>
 */

import { getSharedWebSocket } from './websocket-manager.js';
import { Message, MessageHistory } from './templates.js';
import { formatDate, formatTime, _ } from './utility.js';


/**
 * Inicjalizuje embedded chat dla podanego elementu DOM.
 * @param {HTMLElement} container  - div.embedded-chat z data-room-id i data-csrf
 */
async function initEmbeddedChat(container) {
    const roomId = parseInt(container.dataset.roomId, 10);
    if (!roomId) return;

    const EC_MAX = window.SITE_SETTINGS?.messageMaxLength ?? 500;

    // ── 1. Zbuduj HTML widgetu ────────────────────────────────────────────────
    container.innerHTML = `
        <div class="ec-wrapper">
            <div class="ec-messages messages" id="ec-messages-${roomId}">
                <div class="ec-loading">Ładowanie…</div>
            </div>
            <div class="ec-input-area">
                <div class="reply-preview" id="ec-reply-preview-${roomId}" style="display:none">
                    <span class="reply-preview-label">↩ </span>
                    <span class="reply-preview-text" id="ec-reply-preview-text-${roomId}"></span>
                    <button class="reply-preview-close ec-reply-cancel" type="button" title="Anuluj odpowiedź">✕</button>
                </div>
                <div class="chat-controls-row ec-form-row" id="ec-form-row-${roomId}">
                    <div id="ec-input-${roomId}" class="message-input-rich" role="textbox"
                         contenteditable="true" aria-multiline="true"
                         data-placeholder="${_('Divide the message into several parts...')}"></div>
                    <button class="send-message chat-control btn btn-primary ec-send-btn" id="ec-send-${roomId}" type="button">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <div class="fmt-toolbar">
                    <button class="fmt-btn" data-cmd="bold"      type="button" title="Ctrl+B"><b>B</b></button>
                    <button class="fmt-btn" data-cmd="italic"    type="button" title="Ctrl+I"><i>I</i></button>
                    <button class="fmt-btn" data-cmd="underline" type="button" title="Ctrl+U"><u>U</u></button>
                </div>
                <div class="msg-counter" id="ec-counter-${roomId}">
                    <span id="ec-counter-val-${roomId}">${EC_MAX}</span> / ${EC_MAX}
                </div>
            </div>
        </div>
    `;

    const messagesEl = container.querySelector(`#ec-messages-${roomId}`);
    const inputEl    = container.querySelector(`#ec-input-${roomId}`);
    const sendBtn    = container.querySelector(`#ec-send-${roomId}`);
    const counterEl  = container.querySelector(`#ec-counter-${roomId}`);
    const counterVal = container.querySelector(`#ec-counter-val-${roomId}`);
    const replyPreview     = container.querySelector(`#ec-reply-preview-${roomId}`);
    const replyPreviewText = container.querySelector(`#ec-reply-preview-text-${roomId}`);

    let currentReplyId = null;
    let lastDateBanner = null;

    // ── 2. Helpers ────────────────────────────────────────────────────────────

    function formatMessage(raw) {
        const ALLOWED_TAGS = ['b', 'i', 'u', 'br'];
        const clean = (typeof DOMPurify !== 'undefined')
            ? DOMPurify.sanitize(raw, { ALLOWED_TAGS, ALLOWED_ATTR: [] })
            : raw.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)/g;
        return clean.replace(URL_REGEX, (url) => `<a href="${url}" target="_blank" rel="noopener">${url}</a>`);
    }

    function getInputHtml() {
        const ALLOWED_TAGS = ['b', 'i', 'u', 'br'];
        const BLOCK = new Set(['DIV', 'P', 'SECTION', 'BLOCKQUOTE', 'LI']);
        function serialize(node, isFirst) {
            if (node.nodeType === Node.TEXT_NODE) return node.textContent;
            if (node.nodeType !== Node.ELEMENT_NODE) return '';
            const tag = node.tagName.toUpperCase();
            if (tag === 'BR') return '<br>';
            const inner = Array.from(node.childNodes).map((c, i) => serialize(c, i === 0)).join('');
            if (BLOCK.has(tag)) return (isFirst ? '' : '<br>') + inner;
            if (tag === 'B') return `<b>${inner}</b>`;
            if (tag === 'I') return `<i>${inner}</i>`;
            if (tag === 'U') return `<u>${inner}</u>`;
            return inner;
        }
        const html = Array.from(inputEl.childNodes).map((c, i) => serialize(c, i === 0)).join('');
        return (typeof DOMPurify !== 'undefined')
            ? DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR: [] })
            : html.replace(/<(?!\/?(?:b|i|u|br)\b)[^>]*>/gi, '');
    }

    function updateCounter() {
        const len = (inputEl.textContent || '').length;
        const rem = EC_MAX - len;
        if (counterVal) counterVal.textContent = rem;
        if (!counterEl) return;
        counterEl.classList.remove('counter--warn', 'counter--error');
        if (rem <= 0 || rem <= 10) counterEl.classList.add('counter--error');
        else if (rem <= 50)        counterEl.classList.add('counter--warn');
        if (sendBtn) sendBtn.disabled = rem <= 0;
    }

    function updateToolbarState() {
        container.querySelectorAll('.fmt-btn').forEach(btn => {
            btn.classList.toggle('active', document.queryCommandState(btn.dataset.cmd));
        });
    }

    function appendMessage(msg) {

        const dateStr = formatDate(msg.timestamp);
        if (dateStr !== lastDateBanner) {
            lastDateBanner = dateStr;
            messagesEl.insertAdjacentHTML('beforeend', `<div class="date-banner">${dateStr}</div>`);
        }

        const html = Message({
            room_id:          roomId,
            message_id:       msg.message_id,
            username:         msg.username,
            message:          formatMessage(msg.message),
            upvotes:          msg.upvotes   ?? 0,
            downvotes:        msg.downvotes ?? 0,
            vote:             msg.your_vote ?? null,
            own:              msg.own       ?? false,
            edited:           msg.edited    ?? false,
            attachments:      msg.attachments ?? {},
            original_ts:      msg.timestamp,
            latest_ts:        formatTime(msg.latest_timestamp ?? msg.timestamp),
            type:             null,          // brak głosowania kciukami w embedded
            reply_to:         msg.reply_to  ?? null,
            reactions:        msg.reactions  ?? { bulb: 0, question: 0 },
            your_reactions:   msg.your_reactions ?? [],
            read_by:          msg.read_by   ?? [],
        });
        messagesEl.insertAdjacentHTML('beforeend', html);
        if (msg.your_vote) {
            const msgDiv = messagesEl.querySelector(`.message[data-message-id="${msg.message_id}"]`);
            msgDiv?.querySelector(`.msg-vote[data-event-name="${msg.your_vote}"]`)?.classList.add('active');
        }
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function updateMessage({ message_id, message, latest_timestamp }) {
        const msgDiv = messagesEl.querySelector(`.message[data-message-id="${message_id}"]`);
        if (!msgDiv) return;
        const textEl = msgDiv.querySelector('.msg-text');
        const timeEl = msgDiv.querySelector('.message-timestamp');
        if (textEl) textEl.innerHTML = formatMessage(message);
        if (timeEl) timeEl.textContent = formatTime(latest_timestamp);
    }

    function setReplyTarget(message_id, username, snippet) {
        currentReplyId = message_id;
        if (replyPreview && replyPreviewText) {
            replyPreviewText.textContent = `${username}: ${snippet}`;
            replyPreview.style.display = '';
        }
    }

    function clearReplyTarget() {
        currentReplyId = null;
        if (replyPreview) replyPreview.style.display = 'none';
    }

    function sendMessage() {
        const html = getInputHtml();
        const text = (inputEl.textContent || '').trim();
        if (!text || !joined) return;
        if (text.length > EC_MAX) return;
        ws.sendJson({
            command: 'send',
            room_id: roomId,
            message: html,
            is_anonymous: false,
            attachments: {},
            ...(currentReplyId ? { reply_to_id: currentReplyId } : {}),
        });
        inputEl.innerHTML = '';
        clearReplyTarget();
        updateCounter();
    }

    // ── 3. WebSocket ──────────────────────────────────────────────────────────
    const ws = getSharedWebSocket();
    let joined = false;
    let pendingMessages = [];
    let joinDone = false;

    function joinRoom() {
        if (joined) return;
        ws.sendJsonAsync({ command: 'join', room_id: roomId })
            .then(() => {
                joined = true;
                setTimeout(() => {
                    joinDone = true;
                    messagesEl.innerHTML = '';
                    lastDateBanner = null;
                    for (const msg of pendingMessages) appendMessage(msg);
                    pendingMessages = [];
                    if (messagesEl.children.length === 0) {
                        messagesEl.innerHTML = '<div class="ec-empty empty-chat-message">Brak wiadomości. Napisz pierwszy!</div>';
                    }
                }, 0);
            })
            .catch(err => {
                messagesEl.innerHTML = '<div class="ec-loading">Brak dostępu do tego czatu.</div>';
                console.error('embedded chat join error:', err);
            });
    }

    function onMessage(data) {
        if (data.messages) {
            for (const msg of data.messages) {
                if (msg.room_id && msg.room_id !== roomId) continue;
                if (!joinDone) pendingMessages.push(msg);
                else appendMessage(msg);
            }
        }
        if (data.edit_message) {
            updateMessage(data.edit_message);
        }
        if (data.update_reactions) {
            const ev = data.update_reactions;
            const msgDiv = messagesEl.querySelector(`.message[data-message-id="${ev.message_id}"]`);
            if (!msgDiv) return;
            for (const [key, count] of Object.entries(ev.counts || {})) {
                const btn = msgDiv.querySelector(`.reaction-btn[data-reaction="${key}"]`);
                if (!btn) continue;
                const countEl = btn.querySelector('.reaction-count');
                if (count > 0) {
                    if (countEl) countEl.textContent = count;
                    else btn.insertAdjacentHTML('beforeend', `<span class="reaction-count">${count}</span>`);
                } else if (countEl) countEl.remove();
            }
            if (ev.your_reaction != null) {
                const btn = msgDiv.querySelector(`.reaction-btn[data-reaction="${ev.your_reaction}"]`);
                if (btn) btn.classList.toggle('reaction-btn--active', ev.added ?? false);
            }
        }
        if (data.update_votes) {
            const ev = data.update_votes;
            const msgDiv = messagesEl.querySelector(`.message[data-message-id="${ev.message_id}"]`);
            if (!msgDiv) return;
            const upEl = msgDiv.querySelector('.msg-upvotes');
            const dnEl = msgDiv.querySelector('.msg-downvotes');
            if (upEl) upEl.textContent = ev.upvotes;
            if (dnEl) dnEl.textContent = ev.downvotes;
            if (ev.your_vote) {
                msgDiv.querySelectorAll('.msg-vote').forEach(b => b.classList.remove('active'));
                if (ev.add) msgDiv.querySelector(`.msg-vote[data-event-name="${ev.your_vote}"]`)?.classList.add('active');
            }
        }
    }

    ws.addMessageHandler(onMessage);

    if (ws.socket.readyState === WebSocket.OPEN) {
        joinRoom();
    } else {
        ws.socket.addEventListener('open', function onOpen() {
            ws.socket.removeEventListener('open', onOpen);
            joinRoom();
        });
    }

    // ── 4. Eventy UI ──────────────────────────────────────────────────────────

    inputEl.addEventListener('input', updateCounter);

    inputEl.addEventListener('paste', (e) => {
        e.preventDefault();
        const pasted = (e.clipboardData || window.clipboardData).getData('text');
        const currentLen = (inputEl.textContent || '').length;
        const sel = window.getSelection();
        const selLen = sel?.toString().length ?? 0;
        const available = EC_MAX - currentLen + selLen;
        document.execCommand('insertText', false, pasted.slice(0, Math.max(0, available)));
        updateCounter();
    });

    inputEl.addEventListener('keydown', (e) => {
        const mod = e.ctrlKey || e.metaKey;
        if (mod && e.key === 'b') { e.preventDefault(); document.execCommand('bold');      updateToolbarState(); return; }
        if (mod && e.key === 'i') { e.preventDefault(); document.execCommand('italic');    updateToolbarState(); return; }
        if (mod && e.key === 'u') { e.preventDefault(); document.execCommand('underline'); updateToolbarState(); return; }
        if (e.key === 'Enter' && mod) { e.preventDefault(); submitInput(); return; }
        // zwykły Enter = nowa linia (domyślne zachowanie contenteditable)
    });

    document.addEventListener('selectionchange', () => {
        if (document.activeElement === inputEl) updateToolbarState();
    });

    container.querySelectorAll('.fmt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.execCommand(btn.dataset.cmd);
            inputEl.focus();
            updateToolbarState();
        });
    });

    // Anuluj odpowiedź
    container.querySelector('.ec-reply-cancel')?.addEventListener('click', clearReplyTarget);

    // Delegacja kliknięć wewnątrz messagesEl
    messagesEl.addEventListener('click', (e) => {
        // Cytowanie
        const replyBtn = e.target.closest('.reply-btn');
        if (replyBtn) {
            setReplyTarget(
                replyBtn.dataset.messageId,
                replyBtn.dataset.username,
                replyBtn.dataset.snippet,
            );
            inputEl.focus();
            return;
        }

        // Skocz do cytowanej wiadomości
        const jumpBtn = e.target.closest('.msg-quote-jump');
        if (jumpBtn) {
            const target = messagesEl.querySelector(`.message[data-message-id="${jumpBtn.dataset.targetId}"]`);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                target.classList.remove('msg-highlighted');
                void target.offsetWidth;
                target.classList.add('msg-highlighted');
                setTimeout(() => target.classList.remove('msg-highlighted'), 2000);
            }
            return;
        }

        // Reakcje emoji
        const reactionBtn = e.target.closest('.reaction-btn');
        if (reactionBtn && joined) {
            ws.sendJson({ command: 'message-react', reaction: reactionBtn.dataset.reaction, message_id: parseInt(reactionBtn.dataset.messageId) });
            return;
        }

        // Edytuj własną wiadomość
        const editBtn = e.target.closest('.edit-message');
        if (editBtn) {
            const msgDiv = messagesEl.querySelector(`.message[data-message-id="${editBtn.dataset.messageId}"]`);
            const msgText = msgDiv?.querySelector('.msg-text')?.innerHTML ?? '';
            inputEl.dataset.editMessage = editBtn.dataset.messageId;
            inputEl.innerHTML = msgText;
            inputEl.style.borderColor = 'var(--color-warning)';
            inputEl.focus();
            updateCounter();
            return;
        }

        // Głosowanie
        const voteBtn = e.target.closest('.msg-vote');
        if (voteBtn && joined) {
            const isAdd = !voteBtn.classList.contains('active');
            ws.sendJson({
                command: isAdd ? 'message-add-vote' : 'message-remove-vote',
                vote: voteBtn.dataset.eventName,
                message_id: parseInt(voteBtn.dataset.messageId),
            });
            return;
        }
    });

    function submitInput() {
        if (inputEl.dataset.editMessage) {
            ws.sendJson({ command: 'edit-message', message_id: parseInt(inputEl.dataset.editMessage), new_message: getInputHtml() });
            delete inputEl.dataset.editMessage;
            inputEl.innerHTML = '';
            inputEl.style.borderColor = '';
            updateCounter();
        } else {
            sendMessage();
        }
    }

    sendBtn.addEventListener('click', submitInput);

    inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && inputEl.dataset.editMessage) {
            delete inputEl.dataset.editMessage;
            inputEl.innerHTML = '';
            inputEl.style.borderColor = '';
            updateCounter();
        }
    });

    // ── 5. Cleanup ────────────────────────────────────────────────────────────
    window.addEventListener('beforeunload', () => {
        ws.removeMessageHandler(onMessage);
        if (joined) ws.sendJson({ command: 'leave', room_id: roomId });
    });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    for (const el of document.querySelectorAll('.embedded-chat[data-room-id]')) {
        initEmbeddedChat(el);
    }
});
