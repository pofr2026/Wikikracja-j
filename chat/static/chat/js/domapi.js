/**
 * @file
 * DOM API module providing a clean interface for DOM manipulation operations.
 * Handles all UI updates, element queries, and DOM-related functionality for the chat application.
 */

import {
    removeNotification,
    formatTime,
    escapeHtml,
    _,
    setCaretPosition,
    $,
    $$
} from './utility.js';
import { Room, Message } from './templates.js';

/**
 * DOM API class for managing chat interface DOM operations
 * @class
 */
export default class DomApi {
    getRoomLinkDiv(room_id) {
        return $(`.room-link[data-room-id="${room_id}"]`);
    }

    createRoomDiv(room_id, title, is_public, notifs_enabled) {
        const messageMaxLength = window.SITE_SETTINGS?.messageMaxLength ?? 500;
        const html = Room({ room_id, title, is_public, notifs_enabled, messageMaxLength });
        const container = $('.chat-root-messages');
        // Preserve the folded room header when clearing container
        const foldedHeader = $('#folded-room-header');
        container.innerHTML = '';
        if (foldedHeader) container.appendChild(foldedHeader);
        container.insertAdjacentHTML('beforeend', html);
        return container.firstElementChild;
    }

    getRoom() {
        return $('#room');
    }

    getMessagesDiv() {
        const room = this.getRoom();
        return room ? $('.messages', room) : null;
    }

    addMessage(room_id, message_id, username, message, upvotes, downvotes, vote, own, edited, attachments, original_ts, latest_ts, reply_to = null, reactions = null, your_reactions = null, read_by = null) {
        const html = Message({
            room_id, message_id, username,
            message: this.formatMessage(message),
            upvotes, downvotes, vote, own, edited, attachments,
            original_ts, latest_ts: formatTime(latest_ts),
            type: this.getRoomType(room_id),
            reply_to,
            reactions: reactions ?? { bulb: 0, question: 0 },
            your_reactions: your_reactions ?? [],
            read_by: read_by ?? [],
        });

        this.getMessagesDiv()?.insertAdjacentHTML('beforeend', html);
        this.getVoteDiv(message_id, vote)?.classList.add('active');
    }

    getMessageDiv(message_id) {
        return $(`.message[data-message-id="${message_id}"]`);
    }

    scrollToMessage(message_id) {
        const message = this.getMessageDiv(message_id);
        if (!message) return false;
        message.scrollIntoView();
        message.classList.add('msg-highlight');
        setTimeout(() => message.classList.remove('msg-highlight'), 5000);
        return true;
    }

    updateVoteBar(message_id, upvotes, downvotes) {
        const msgDiv = this.getMessageDiv(message_id);
        if (!msgDiv) return;
        const total = upvotes + downvotes;
        const barWrap = $('.vote-bar-wrap', msgDiv);
        const barFill = $('.vote-bar-fill', msgDiv);
        const barLabel = $('.vote-bar-label', msgDiv);
        if (total >= 3) {
            const pct = Math.round((upvotes / total) * 100);
            const cls = pct >= 60 ? 'vote-bar--positive' : (pct >= 40 ? 'vote-bar--neutral' : 'vote-bar--negative');
            if (barFill) {
                barFill.style.width = `${pct}%`;
                barFill.className = `vote-bar-fill ${cls}`;
            }
            if (barLabel) barLabel.textContent = `${pct}% popiera`;
            if (barWrap) barWrap.style.display = '';
            if (barLabel) barLabel.style.display = '';
        } else {
            if (barWrap) barWrap.style.display = 'none';
            if (barLabel) barLabel.style.display = 'none';
        }
    }

    getMessageUpvotesCountDiv(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? $(".msg-upvotes", msgDiv) : null;
    }

    getMessageDownvotesCountDiv(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? $(".msg-downvotes", msgDiv) : null;
    }

    getVoteDiv(message_id, vote) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? $(`.msg-vote[data-event-name="${vote}"]`, msgDiv) : null;
    }

    editMessageText(message_id, text, ts) {
        this.getMessageTimeDiv(message_id).textContent = formatTime(ts);
        const msgDiv = this.getMessageDiv(message_id);
        if (msgDiv) {
            const msgText = $(".msg-text", msgDiv);
            if (msgText) {
                msgText.innerHTML = this.formatMessage(text);
                return msgText;
            }
        }
        return null;
    }

    updateMessageAttachments(message_id, attachments) {
        const message_div = this.getMessageDiv(message_id);
        if (!message_div) return;
        const attachment_container = $('.attachment-image-container', message_div);
        if (attachment_container) {
            attachment_container.innerHTML = '';
            if (attachments?.images?.length > 0) {
                for (const filename of attachments.images) {
                    attachment_container.insertAdjacentHTML('beforeend', `<img class='attached-image' src='/media/uploads/${filename}'>`);
                }
            }
        }
    }

    showHistoryButton(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        if (msgDiv) {
            $(".show-history", msgDiv).style.display = '';
        }
    }

    getRoomType(room_id) {
        return $(`.room-link[data-room-id="${room_id}"]`)?.getAttribute("data-room-type") ?? null;
    }

    getLastMessageBanner() {
        const messagesDiv = this.getMessagesDiv();
        return messagesDiv ? $$('.date-banner', messagesDiv) : [];
    }

    getMessageText(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        if (!msgDiv) return '';
        const msgText = $(".msg-text", msgDiv);
        if (!msgText) return '';
        // Return innerHTML to preserve rich text formatting
        return msgText.innerHTML ?? '';
    }

    formatMessage(raw_message) {
        const ALLOWED_TAGS = ['b', 'i', 'u', 'br'];
        const clean = (typeof DOMPurify !== 'undefined')
            ? DOMPurify.sanitize(raw_message, { ALLOWED_TAGS, ALLOWED_ATTR: [] })
            : escapeHtml(raw_message);
        const URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)/g;
        return clean.replace(URL_REGEX, (match) => {
            const isInternal = match.replace(/^https?/, 'http').startsWith(window.location.origin.replace(/^https?/, 'http'));
            return `<a href='${match}'${isInternal ? '' : ' target="_blank" rel="noopener"'}>${match}</a>`;
        });
    }

    getPreviewDiv() {
        return $(".preview-images");
    }

    getPreviewContainer() {
        return $(`.image-preview-container`);
    }

    seenChat(room_id) {
        const roomLink = this.getRoomLinkDiv(room_id);
        roomLink?.classList.remove("room-not-seen");
        // Swap unread dot → read circle
        const unreadDot = roomLink?.querySelector('.nav-status--unread');
        if (unreadDot) {
            unreadDot.classList.remove('nav-status--unread');
            unreadDot.classList.add('nav-status--read');
            unreadDot.removeAttribute('aria-label');
            unreadDot.setAttribute('aria-hidden', 'true');
        }
        this.setRoomSeenIconState(room_id, true);
        if ($$('.room-not-seen').length === 0) {
            removeNotification();
        }
        // Trigger unread filter update if it's active
        if (typeof window.updateUnreadFilter === 'function') {
            window.updateUnreadFilter();
        }
    }

    updateOnline(room_id, is_online) {
        const room_link = this.getRoomLinkDiv(room_id);
        if (!room_link) return;
        room_link.classList.toggle('online', is_online);
        room_link.classList.toggle('offline', !is_online);
    }

    getMessageTimeDiv(message_id) {
        return $(`.message-timestamp[data-message-id="${message_id}"]`);
    }

    getMessageInput() {
        return $(`#message-input`);
    }

    getEnteredText() {
        const el = this.getMessageInput();
        if (!el) return '';
        if (el.isContentEditable) {
            const ALLOWED_TAGS = ['b', 'i', 'u', 'br'];
            // Walk the DOM and serialize to HTML, converting block elements to <br>
            // so that newlines entered by the user are preserved.
            const BLOCK = new Set(['DIV', 'P', 'SECTION', 'ARTICLE', 'BLOCKQUOTE', 'LI']);
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
            const html = Array.from(el.childNodes).map((c, i) => serialize(c, i === 0)).join('');
            return (typeof DOMPurify !== 'undefined')
                ? DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR: [] })
                : html.replace(/<(?!\/?(?:b|i|u|br)\b)[^>]*>/gi, '');
        }
        return el.value ?? '';
    }

    getVisibleTextLength() {
        const el = this.getMessageInput();
        if (!el) return 0;
        return el.isContentEditable ? (el.textContent || '').length : (el.value || '').length;
    }

    getAnonymousValue() {
        return $(`#anonymous-toggle`)?.classList.contains('active') ?? false;
    }

    getFileInput() {
        return $(`#file-input`);
    }

    getFiles() {
        return this.getFileInput()?.files ?? null;
    }

    clearFiles() {
        const fileInput = $(`#file-input`);
        if (fileInput) fileInput.value = "";
        this.getPreviewContainer().style.display = 'none';
        this.getPreviewDiv().innerHTML = '';
    }

    getEditedMessageId() {
        return this.getMessageInput()?.dataset.editMessage ?? null;
    }

    setEditing(message_id) {
        const text = this.getMessageText(message_id);
        this.getFileInput()?.removeAttribute('disabled');
        const input = this.getMessageInput();
        if (input) {
            input.dataset.editMessage = message_id;
            input.dataset.originalMessageText = text;
            if (input.isContentEditable) {
                input.textContent = text;
            } else {
                input.value = text;
            }
            input.style.borderColor = 'var(--color-warning)';
        }
        this.loadEditingAttachments(message_id, this.getMessageAttachments(message_id));
        if (input?.isContentEditable) {
            input.focus();
            const range = document.createRange();
            range.selectNodeContents(input);
            range.collapse(false);
            window.getSelection()?.removeAllRanges();
            window.getSelection()?.addRange(range);
        } else {
            setCaretPosition(this.getMessageInput(), text.length);
        }
        input?.dispatchEvent(new Event('input'));
    }

    stopEditing() {
        this.getFileInput()?.removeAttribute('disabled');
        const input = this.getMessageInput();
        if (input) {
            delete input.dataset.editMessage;
            delete input.dataset.removedAttachments;
            delete input.dataset.originalMessageText;
            if (input.isContentEditable) {
                input.innerHTML = '';
            } else {
                input.value = '';
            }
            input.style.borderColor = '';
            input.dispatchEvent(new Event('input'));
        }
        this.clearFiles();
    }

    openBigImage(srcs) {
        // Remove existing viewer if any
        this.closeBigImage();

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'image-viewer-overlay';
        overlay.className = 'image-viewer-overlay';
        overlay.innerHTML = `
            <button class="image-viewer-close" aria-label="Close">&times;</button>
            <button class="image-viewer-nav image-viewer-prev" aria-label="Previous">&#10094;</button>
            <button class="image-viewer-nav image-viewer-next" aria-label="Next">&#10095;</button>
            <div class="image-viewer-container">
                <img class="image-viewer-img" src="" alt="Image viewer">
            </div>
            <div class="image-viewer-counter"></div>
        `;

        document.body.appendChild(overlay);
        document.body.classList.add('modal-open');

        // State
        let currentIndex = 0;
        const images = srcs;
        const imgEl = overlay.querySelector('.image-viewer-img');
        const counterEl = overlay.querySelector('.image-viewer-counter');
        const prevBtn = overlay.querySelector('.image-viewer-prev');
        const nextBtn = overlay.querySelector('.image-viewer-next');

        function showImage(index) {
            currentIndex = index;
            imgEl.src = images[currentIndex];
            if (images.length > 1) {
                counterEl.textContent = (currentIndex + 1) + ' / ' + images.length;
                prevBtn.style.display = 'block';
                nextBtn.style.display = 'block';
            } else {
                counterEl.textContent = '';
                prevBtn.style.display = 'none';
                nextBtn.style.display = 'none';
            }
        }

        function close() {
            overlay.remove();
            document.body.classList.remove('modal-open');
        }

        // Event listeners
        overlay.querySelector('.image-viewer-close').addEventListener('click', close);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) close();
        });

        prevBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const newIndex = (currentIndex - 1 + images.length) % images.length;
            showImage(newIndex);
        });

        nextBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const newIndex = (currentIndex + 1) % images.length;
            showImage(newIndex);
        });

        // Keyboard navigation
        overlay._keyHandler = (e) => {
            if (e.key === 'Escape') close();
            if (e.key === 'ArrowLeft' && images.length > 1) showImage((currentIndex - 1 + images.length) % images.length);
            if (e.key === 'ArrowRight' && images.length > 1) showImage((currentIndex + 1) % images.length);
        };
        document.addEventListener('keydown', overlay._keyHandler);

        // Show first image
        showImage(0);
    }

    closeBigImage() {
        const overlay = $('#image-viewer-overlay');
        if (overlay) {
            if (overlay._keyHandler) {
                document.removeEventListener('keydown', overlay._keyHandler);
            }
            overlay.remove();
        }
        document.body.classList.remove('modal-open');
    }

    getLatestOwnMessage() {
        const messagesDiv = this.getMessagesDiv();
        if (!messagesDiv) return null;
        const ownMessages = $$('.message.own', messagesDiv);
        return ownMessages.length > 0 ? ownMessages[ownMessages.length - 1] : null;
    }

    isEditing() {
        return !!this.getEditedMessageId();
    }

    removeNoMessagesBanner() {
        $('.empty-chat-message')?.remove();
    }

    setRoomTitle(title) {
        const el = $("#room-title");
        if (el) el.textContent = title;
    }

    setRoomNotifications(room_id, is_enabled) {
        const btn = $(`.notif-switch[data-room-id='${room_id}']`);
        if (!btn) return;
        btn.disabled = false;
        btn.dataset.enabled = is_enabled;
        const icon = $("i", btn);
        if (icon) {
            icon.classList.toggle('fa-bell', is_enabled);
            icon.classList.toggle('fa-bell-slash', !is_enabled);
        }
    }

    setRoomSeenIconState(room_id, is_seen) {
        const btn = $(`.seen-switch[data-room-id='${room_id}']`);
        if (!btn) return;
        btn.dataset.seen = is_seen.toString();
        const icon = $("i", btn);
        if (icon) {
            icon.classList.toggle('fa-eye', is_seen);
            icon.classList.toggle('fa-eye-slash', !is_seen);
        }
    }

    clearRoomData() {
        const messagesDiv = this.getMessagesDiv();
        if (messagesDiv) messagesDiv.innerHTML = '';
        this.clearFiles();
        this.stopEditing();
        messagesDiv?.insertAdjacentHTML('beforeend', "<p class='empty-chat-message'>" + _("Loading...") + "</p>");
    }

    showCopyFeedback(button, message, success) {
        if (!button) return;
        const tooltip = document.createElement('span');
        tooltip.className = "copy-feedback badge";
        tooltip.textContent = message;
        tooltip.classList.add(success ? 'text-bg-success' : 'text-bg-danger');
        button.appendChild(tooltip);
        setTimeout(() => {
            tooltip.style.transition = 'opacity 0.2s';
            tooltip.style.opacity = '0';
            setTimeout(() => tooltip.remove(), 200);
        }, 1200);
    }

    getMessageAttachments(message_id) {
        const message_div = this.getMessageDiv(message_id);
        const attachments = { images: [] };
        if (message_div) {
            $$('.attached-image', message_div).forEach(img => {
                attachments.images.push(img.getAttribute('src').split('/').pop());
            });
        }
        return attachments.images.length > 0 ? attachments : {};
    }

    loadEditingAttachments(message_id, attachments) {
        const preview_container = this.getPreviewDiv();
        if (preview_container) preview_container.innerHTML = '';
        if (!attachments?.images?.length) {
            this.getPreviewContainer().style.display = 'none';
            return;
        }
        this.getPreviewContainer().style.display = '';
        for (let i = 0; i < attachments.images.length; i++) {
            const filename = attachments.images[i];
            preview_container?.insertAdjacentHTML('beforeend', `<div class="image-preview-wrapper" style="position: relative; display: inline-block;">
                <img class='image-preview' id='preview-existing-${i}' src='/media/uploads/${filename}' data-filename='${filename}'>
                <button class="btn btn-sm btn-danger remove-existing-attachment"
                    style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 12px;"
                    data-filename="${filename}" type="button">×</button>
            </div>`);
        }
    }

    getRemovedAttachments() {
        const input = this.getMessageInput();
        return input?.dataset.removedAttachments ? JSON.parse(input.dataset.removedAttachments) : [];
    }

    addRemovedAttachment(filename) {
        const removed = this.getRemovedAttachments();
        if (!removed.includes(filename)) {
            removed.push(filename);
            this.getMessageInput().dataset.removedAttachments = JSON.stringify(removed);
        }
    }

    getOriginalMessageText(message_id) {
        return this.getMessageInput()?.dataset.originalMessageText ?? '';
    }

    /**
     * Update the sticky breadcrumb above the message list.
     * @param {Array<{label: string, active?: boolean}>} parts
     */
    updateBreadcrumb(parts) {
        const bc = $('#chat-breadcrumb');
        if (!bc) return;
        bc.innerHTML = parts.map((p, i) =>
            `<span class="bc-seg${p.active ? ' bc-seg--active' : ''}">${p.label}</span>` +
            (i < parts.length - 1 ? '<span class="bc-sep" aria-hidden="true"> › </span>' : '')
        ).join('');
    }

    /**
     * Set the room title in the folded header (mobile back button area)
     * @param {string} title - Room title to display
     */
    setFoldedRoomTitle(title) {
        const el = $("#folded-room-title");
        if (el) el.textContent = title;
    }

    /**
     * Show the folded room header (mobile back button) and add class to collapse room list
     * Only applies to mobile screens (< 768px) via CSS media queries
     */
    showFoldedRoomHeader() {
        const chatRooms = $(".chat-rooms");
        if (chatRooms) chatRooms.classList.add('mobile-room-selected');
    }

    /**
     * Hide the folded room header and remove class to show room list
     */
    hideFoldedRoomHeader() {
        const chatRooms = $(".chat-rooms");
        if (chatRooms) chatRooms.classList.remove('mobile-room-selected');
    }

}
