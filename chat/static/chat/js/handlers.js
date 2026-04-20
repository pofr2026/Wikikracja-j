/**
 * @file
 * Event handlers module for chat UI interactions.
 * Sets up DOM event listeners and routes events to appropriate handler functions.
 */

import {
    onSubmitMessage,
    onUpdateVote,
    onRoomTryJoin,
    onBackToRoomList,
    onToggleNotifications,
    onToggleSeen,
    onMessageHistory,
    copyRoomLink,
    copyMessageLink,
    setReplyTarget,
    clearReplyTarget,
    onToggleReaction,
} from './chat.js';
import DomApi from './domapi.js';
import { $, $$ } from './utility.js';

/**
 * DOM API instance for UI operations
 * @type {DomApi}
 */
const DOM_API = new DomApi();

document.addEventListener('DOMContentLoaded', () => {
    // Auto-resize textarea functionality
    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    // ---- ZMIANA 5: Character counter ----
    const MSG_MAX = window.SITE_SETTINGS?.messageMaxLength ?? 500;

    function updateCounter(text) {
        const remaining = MSG_MAX - text.length;
        const counterVal = $('#msg-counter-val');
        if (!counterVal) return;
        counterVal.textContent = remaining;
        const row = $('#msg-counter');
        if (!row) return;
        row.classList.remove('counter--warn', 'counter--error');
        const input = $('#message-input');
        if (remaining <= 0) {
            row.classList.add('counter--error');
            input?.classList.add('input--error');
        } else if (remaining <= 10) {
            row.classList.add('counter--error');
            input?.classList.remove('input--error');
        } else if (remaining <= 50) {
            row.classList.add('counter--warn');
            input?.classList.remove('input--error');
        } else {
            input?.classList.remove('input--error');
        }
        const sendBtn = $('.send-message');
        if (sendBtn) sendBtn.disabled = remaining <= 0;
    }

    function showToast(message) {
        const existing = document.getElementById('chat-toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.id = 'chat-toast';
        toast.className = 'chat-toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('chat-toast--visible'));
        setTimeout(() => {
            toast.classList.remove('chat-toast--visible');
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }

    // ---- ZMIANA 6: Rich text toolbar state ----
    function updateToolbarState() {
        ['bold', 'italic', 'underline'].forEach(cmd => {
            const btn = $(`[data-cmd="${cmd}"]`);
            btn?.classList.toggle('active', document.queryCommandState(cmd));
        });
    }

    // Update counter on input; no auto-resize needed for contenteditable
    document.addEventListener('input', (e) => {
        if (e.target.id === 'message-input') {
            const el = e.target;
            const text = el.isContentEditable ? (el.textContent || '') : el.value;
            updateCounter(text);
        }
    });

    // Paste interception: strip HTML and truncate if over limit
    document.addEventListener('paste', (e) => {
        if (e.target.id !== 'message-input') return;
        const el = e.target;
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        if (el.isContentEditable) {
            const currentLength = (el.textContent || '').length;
            const sel = window.getSelection();
            const selectedLength = sel?.toString().length ?? 0;
            const newLength = currentLength - selectedLength + pastedText.length;
            if (newLength > MSG_MAX) {
                e.preventDefault();
                const available = MSG_MAX - currentLength + selectedLength;
                if (available > 0) {
                    document.execCommand('insertText', false, pastedText.slice(0, available));
                }
                updateCounter(el.textContent || '');
                showToast('Wiadomość przycięta do ' + MSG_MAX + ' znaków');
            } else {
                // Always paste as plain text to avoid injecting foreign HTML
                e.preventDefault();
                document.execCommand('insertText', false, pastedText);
            }
        } else {
            const val = el.value;
            const start = el.selectionStart;
            const end = el.selectionEnd;
            const newVal = val.slice(0, start) + pastedText + val.slice(end);
            if (newVal.length > MSG_MAX) {
                e.preventDefault();
                const truncated = newVal.slice(0, MSG_MAX);
                el.value = truncated;
                el.selectionStart = el.selectionEnd = Math.min(start + pastedText.length, MSG_MAX);
                autoResizeTextarea(el);
                updateCounter(truncated);
                showToast('Wiadomość przycięta do ' + MSG_MAX + ' znaków');
            }
        }
    });
    // ---- ZMIANA 1: Tree sidebar — nav-cat-btn collapse/expand ----
    // Restore cat states from localStorage (before click handler, so initial state is set)
    document.querySelectorAll('.nav-cat-btn').forEach(btn => {
        const contentId = btn.dataset.catContent;
        if (!contentId) return;
        const content = document.getElementById(contentId);
        if (!content) return;
        const savedState = localStorage.getItem(`chat-cat-${contentId}`);
        if (savedState === 'collapsed') {
            content.classList.remove('open');
            btn.setAttribute('aria-expanded', 'false');
        } else {
            // Default: expanded
            content.classList.add('open');
            btn.setAttribute('aria-expanded', 'true');
        }
    });

    // Restore archive section states from localStorage
    const archiveTargets = ['pub-rooms-archive', 'tasks-archive', 'votes-archive', 'prv-archive'];
    archiveTargets.forEach(targetId => {
        const archiveSection = document.getElementById(`content-${targetId}`);
        const archiveBtn = document.querySelector(`.archive-toggle[data-target="${targetId}"]`);
        if (!archiveSection || !archiveBtn) return;
        const savedState = localStorage.getItem(`chat-archive-${targetId}`);
        const hasUnreadRooms = archiveSection.querySelector('.room-not-seen') !== null;
        if (hasUnreadRooms || savedState === 'visible') {
            archiveSection.classList.add('visible');
            archiveBtn.classList.add('active');
            if (hasUnreadRooms && savedState !== 'visible') {
                localStorage.setItem(`chat-archive-${targetId}`, 'visible');
            }
        } else {
            archiveSection.classList.remove('visible');
            archiveBtn.classList.remove('active');
        }
    });

    // nav-cat-btn click: toggle category open/closed
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.nav-cat-btn');
        if (!btn) return;
        const contentId = btn.dataset.catContent;
        const content = contentId ? document.getElementById(contentId) : null;
        if (!content) return;
        const isOpen = content.classList.contains('open');
        content.classList.toggle('open', !isOpen);
        btn.setAttribute('aria-expanded', String(!isOpen));
        if (contentId) {
            localStorage.setItem(`chat-cat-${contentId}`, isOpen ? 'collapsed' : 'expanded');
        }
    });

    // collapse-all-btn: toggle all categories at once
    document.getElementById('collapse-all-btn')?.addEventListener('click', () => {
        const allOpen = [...document.querySelectorAll('.nav-cat-content')].every(c => c.classList.contains('open'));
        document.querySelectorAll('.nav-cat-btn').forEach(btn => {
            const contentId = btn.dataset.catContent;
            const content = contentId ? document.getElementById(contentId) : null;
            if (!content) return;
            content.classList.toggle('open', !allOpen);
            btn.setAttribute('aria-expanded', String(!allOpen));
            if (contentId) localStorage.setItem(`chat-cat-${contentId}`, allOpen ? 'collapsed' : 'expanded');
        });
        const icon = document.querySelector('#collapse-all-btn i');
        if (icon) icon.className = allOpen ? 'fas fa-angles-down' : 'fas fa-angles-up';
    });

    document.addEventListener("click", (e) => {
        if (e.target.closest(".send-message")) {
            onSubmitMessage(DOM_API.getEnteredText(), DOM_API.getEditedMessageId());
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.target.id !== "message-input") return;
        const el = e.target;
        const mod = e.ctrlKey || e.metaKey;

        // ZMIANA 6: rich text shortcuts
        if (el.isContentEditable) {
            if (mod && e.key === 'b') { e.preventDefault(); document.execCommand('bold');      updateToolbarState(); return; }
            if (mod && e.key === 'i') { e.preventDefault(); document.execCommand('italic');    updateToolbarState(); return; }
            if (mod && e.key === 'u') { e.preventDefault(); document.execCommand('underline'); updateToolbarState(); return; }
            // Ctrl+Enter = wyślij; Enter = nowa linia (domyślne zachowanie contenteditable)
            if (e.key === 'Enter' && mod) {
                e.preventDefault();
                onSubmitMessage(DOM_API.getEnteredText(), DOM_API.getEditedMessageId());
                return;
            }
            // Zwykły Enter: pozwól przeglądarce wstawić nową linię
            return;
        }

        if (e.key === "Enter" && mod) {
            e.preventDefault();
            onSubmitMessage(DOM_API.getEnteredText(), DOM_API.getEditedMessageId());
        }
        if (e.key === "ArrowUp") {
            e.preventDefault();
            const message = DOM_API.getLatestOwnMessage();
            if (!DOM_API.isEditing()) {
                DOM_API.setEditing(message?.dataset.messageId);
            }
        }
    });

    // Toolbar button clicks
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.fmt-btn');
        if (btn) {
            e.preventDefault();
            document.execCommand(btn.dataset.cmd);
            $('#message-input')?.focus();
            updateToolbarState();
        }
    });

    // Update toolbar active state on cursor move
    document.addEventListener('selectionchange', () => {
        if (document.activeElement?.id === 'message-input') {
            updateToolbarState();
        }
    });

    document.addEventListener('click', (e) => {
        const container = e.target.closest('.attachment-image-container');
        if (container) {
            const images = Array.from(container.querySelectorAll('.attached-image'));
            const index = images.indexOf(e.target);
            if (index !== -1) {
                const imageSrcs = images.map(img => img.src);
                DOM_API.openBigImage(imageSrcs);
            }
        }
    });

    document.addEventListener('click', (e) => {
        const archiveBtn = e.target.closest('.archive-toggle');
        if (archiveBtn) {
            const targetId = archiveBtn.dataset.target;
            const archiveSection = document.getElementById(`content-${targetId}`);
            if (archiveSection) {
                const isVisible = archiveSection.classList.contains('visible');
                if (isVisible) {
                    archiveSection.classList.remove('visible');
                    archiveBtn.classList.remove('active');
                    localStorage.setItem(`chat-archive-${targetId}`, 'hidden');
                } else {
                    archiveSection.classList.add('visible');
                    archiveBtn.classList.add('active');
                    localStorage.setItem(`chat-archive-${targetId}`, 'visible');
                }
            }
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.notif-switch');
        if (btn) {
            const newState = !(btn.dataset.enabled === "true" || btn.dataset.enabled === true);
            btn.dataset.enabled = newState;
            const icon = $("i", btn);
            icon?.classList.toggle('fa-bell', newState);
            icon?.classList.toggle('fa-bell-slash', !newState);
            onToggleNotifications(btn.dataset.roomId, newState);
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.seen-switch');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            const isCurrentlySeen = btn.dataset.seen === "true";
            const newState = !isCurrentlySeen;
            DOM_API.getRoomLinkDiv(btn.dataset.roomId)?.classList.toggle('room-not-seen', !newState);
            DOM_API.setRoomSeenIconState(btn.dataset.roomId, newState);
            onToggleSeen(btn.dataset.roomId, newState);
            // Update unread filter if it's active
            if (typeof window.updateUnreadFilter === 'function') {
                window.updateUnreadFilter();
            }
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.track-switch');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            const isTracked = btn.dataset.tracked === 'true';
            const newTracked = !isTracked;
            btn.dataset.tracked = newTracked;
            btn.classList.toggle('active', newTracked);
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = newTracked ? 'fas fa-bookmark' : 'far fa-bookmark';
            }
            const roomDiv = btn.closest('.room-link');
            if (roomDiv) {
                roomDiv.classList.toggle('room-auto-muted', !newTracked && roomDiv.dataset.autoMuted !== 'false');
            }
            fetch('/chat/api/toggle-track/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ room_id: btn.dataset.roomId, tracked: newTracked }),
            });
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.anonymous-toggle');
        if (btn) {
            btn.classList.toggle('active');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === "Escape" && DOM_API.isEditing()) {
            DOM_API.stopEditing();
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.delete-images-preview');
        if (btn) DOM_API.clearFiles(btn.dataset.roomId);
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.copy-room-url');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            copyRoomLink(btn.dataset.roomId, btn);
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.copy-message-url');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            copyMessageLink(btn.dataset.roomId, btn.dataset.messageId, btn);
        }
    });

    document.addEventListener("change", (e) => {
        if (!e.target.classList.contains("file-input")) return;
        const files = e.target.files;
        const preview_container = DOM_API.getPreviewDiv();
        if (!DOM_API.isEditing() && preview_container) preview_container.innerHTML = '';
        if (files.length > 0) DOM_API.getPreviewContainer().style.display = '';
        for (let i = 0; i < files.length; ++i) {
            const file = files.item(i);
            const fr = new FileReader();
            const preview_id = `preview-new-${i}-${Date.now()}`;
            preview_container?.insertAdjacentHTML('beforeend', `<div class="image-preview-wrapper" style="position: relative; display: inline-block;">
                <img class='image-preview new-attachment' id='${preview_id}'>
                <button class="btn btn-sm btn-danger remove-new-attachment"
                    style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 12px;"
                    data-preview-id="${preview_id}" type="button">×</button>
            </div>`);
            fr.onload = (e) => {
                document.getElementById(preview_id).src = e.target.result;
            };
            fr.readAsDataURL(file);
        }
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".msg-vote");
        if (btn) {
            onUpdateVote.call(btn, btn.dataset.eventName, btn.dataset.messageId, !btn.classList.contains('active'));
        }
    });

    // ---- ZMIANA 4B: Emoji reaction toggle ----
    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".reaction-btn");
        if (btn) {
            const reaction = btn.dataset.reaction;
            const messageId = btn.dataset.messageId;
            if (reaction && messageId) {
                onToggleReaction(reaction, parseInt(messageId));
            }
        }
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".show-history");
        if (btn) onMessageHistory(btn.dataset.messageId);
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".edit-message");
        if (btn) DOM_API.setEditing(btn.dataset.messageId);
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".remove-existing-attachment");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            DOM_API.addRemovedAttachment(btn.dataset.filename);
            btn.closest('.image-preview-wrapper')?.remove();
            if (DOM_API.getPreviewDiv()?.children.length === 0) {
                DOM_API.getPreviewContainer().style.display = 'none';
            }
        }
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".remove-new-attachment");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            btn.closest('.image-preview-wrapper')?.remove();
            const previewDiv = DOM_API.getPreviewDiv();
            if (previewDiv && $$('.new-attachment', previewDiv).length === 0) {
                DOM_API.getFileInput().value = "";
            }
            if (previewDiv?.children.length === 0) {
                DOM_API.getPreviewContainer().style.display = 'none';
            }
        }
    });

    // ---- ZMIANA 2: Quote/Reply ----
    let _replySourceMessageId = null; // ID of the message containing the clicked quote jump

    document.addEventListener('click', (e) => {
        // Reply button — set reply target
        const replyBtn = e.target.closest('.reply-btn');
        if (replyBtn) {
            const msgId = replyBtn.dataset.messageId;
            const username = replyBtn.dataset.username;
            const snippet = replyBtn.dataset.snippet;
            setReplyTarget(msgId, username, snippet);
            $('#message-input')?.focus();
            return;
        }
    });

    document.addEventListener('click', (e) => {
        // Cancel reply
        if (e.target.closest('#reply-preview-close')) {
            clearReplyTarget();
            return;
        }
    });

    document.addEventListener('click', (e) => {
        // Quote jump — scroll to original message
        const jumpBtn = e.target.closest('.msg-quote-jump') || e.target.closest('.msg-quote');
        if (jumpBtn) {
            const targetId = jumpBtn.dataset.targetId || jumpBtn.dataset.replyId
                          || jumpBtn.closest('.msg-quote')?.dataset.replyId;
            const currentMsg = jumpBtn.closest('.message');
            if (currentMsg) _replySourceMessageId = currentMsg.dataset.messageId;

            const targetMsg = document.querySelector(`.message[data-message-id="${targetId}"]`);
            if (targetMsg) {
                targetMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
                targetMsg.classList.remove('msg-highlighted');
                void targetMsg.offsetWidth;
                targetMsg.classList.add('msg-highlighted');
                setTimeout(() => targetMsg.classList.remove('msg-highlighted'), 2000);

                showReturnBtn(targetMsg);
            }
        }
    });

    function showReturnBtn(targetMsg) {
        // Remove any existing return button
        document.getElementById('msg-return-btn')?.remove();

        const btn = document.createElement('button');
        btn.id = 'msg-return-btn';
        btn.type = 'button';
        btn.innerHTML = '↙';
        btn.title = 'Wróć do odpowiedzi';
        const content = targetMsg.querySelector('.message-content') || targetMsg;
        content.appendChild(btn);
        requestAnimationFrame(() => btn.classList.add('visible'));

        // Hide only when user manually scrolls to the bottom (ignore scroll from scrollIntoView)
        const messagesContainer = document.querySelector('#room .messages');
        if (messagesContainer) {
            let listenActive = false;
            // Wait for scrollIntoView animation to finish before attaching listener
            setTimeout(() => { listenActive = true; }, 800);
            const onScroll = () => {
                if (!listenActive) return;
                const atBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < 60;
                if (atBottom) {
                    btn.remove();
                    messagesContainer.removeEventListener('scroll', onScroll);
                }
            };
            messagesContainer.addEventListener('scroll', onScroll);
            btn._removeScroll = () => messagesContainer.removeEventListener('scroll', onScroll);
        }
    }

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('#msg-return-btn');
        if (btn) {
            btn._removeScroll?.();
            btn.remove();
            if (_replySourceMessageId) {
                const src = document.querySelector(`.message[data-message-id="${_replySourceMessageId}"]`);
                src?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                _replySourceMessageId = null;
            }
        }
    });

    document.addEventListener('click', handleRoomNameClick);

    function handleRoomNameClick(e) {
        const roomName = e.target.closest('.room-name');
        if (!roomName) return;
        const room_id = roomName.parentElement.getAttribute("data-room-id");
        if (!roomName.classList.contains("joined")) {
            roomName.parentElement.classList.add('room-tapping');
            setTimeout(() => roomName.parentElement.classList.remove('room-tapping'), 300);
            // Sync eye icon state after joining
            DOM_API.getRoomLinkDiv(room_id)?.classList.remove("room-not-seen");
            DOM_API.setRoomSeenIconState(room_id, true);
            onRoomTryJoin(room_id);
            // Update unread filter if it's active
            if (typeof window.updateUnreadFilter === 'function') {
                window.updateUnreadFilter();
            }
        }
    }

    // Handle back button to room list
    document.addEventListener('click', (e) => {
        const backBtn = e.target.closest('#back-to-room-list');
        if (backBtn) {
            e.preventDefault();
            onBackToRoomList();
        }
    });

    // Handle folded room title click to navigate back to room list
    document.addEventListener('click', (e) => {
        const roomTitle = e.target.closest('#folded-room-title');
        if (roomTitle) {
            e.preventDefault();
            onBackToRoomList();
        }
    });

    // Handle window resize - reset mobile state on larger screens
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 768) {
            const chatRooms = $(".chat-rooms");
            if (chatRooms) chatRooms.classList.remove('mobile-room-selected');
        }
    });
});

function slideToggle(element, duration) {
    const isHidden = element.style.display === 'none' || getComputedStyle(element).display === 'none';
    
    if (isHidden) {
        element.style.display = 'block';
        element.style.height = '0';
        element.style.overflow = 'hidden';
        element.style.transition = `height ${duration}ms ease`;
        requestAnimationFrame(() => {
            element.style.height = element.scrollHeight + 'px';
        });
    } else {
        element.style.height = element.scrollHeight + 'px';
        element.style.overflow = 'hidden';
        element.style.transition = `height ${duration}ms ease`;
        requestAnimationFrame(() => {
            element.style.height = '0';
        });
        element.addEventListener('transitionend', function handler() {
            element.removeEventListener('transitionend', handler);
            element.style.display = 'none';
            element.style.height = '';
            element.style.overflow = '';
        });
    }
}