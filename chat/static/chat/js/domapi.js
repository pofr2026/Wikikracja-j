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
        const html = Room({ room_id, title, is_public, notifs_enabled });
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

    addMessage(room_id, message_id, username, message, upvotes, downvotes, vote, own, edited, attachments, original_ts, latest_ts) {
        const html = Message({
            room_id, message_id, username,
            message: this.formatMessage(message),
            upvotes, downvotes, vote, own, edited, attachments,
            original_ts, latest_ts: formatTime(latest_ts),
            type: this.getRoomType(room_id),
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
        return msgDiv ? $(".msg-text", msgDiv)?.textContent ?? '' : '';
    }

    formatMessage(raw_message) {
        let escaped = escapeHtml(raw_message);
        const URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)/g;
        return escaped.replace(URL_REGEX, (match) => `<a href='${match}' target="_blank">${match}</a>`);
    }

    getPreviewDiv() {
        return $(".preview-images");
    }

    getPreviewContainer() {
        return $(`.image-preview-container`);
    }

    seenChat(room_id) {
        this.getRoomLinkDiv(room_id)?.classList.remove("room-not-seen");
        this.setRoomSeenIconState(room_id, true);
        if ($$('.room-not-seen').length === 0) {
            removeNotification();
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
        return this.getMessageInput()?.value ?? '';
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
            input.value = text;
            input.style.backgroundColor = '#4a4a00';
        }
        this.loadEditingAttachments(message_id, this.getMessageAttachments(message_id));
        setCaretPosition(this.getMessageInput(), text.length);
    }

    stopEditing() {
        this.getFileInput()?.removeAttribute('disabled');
        const input = this.getMessageInput();
        if (input) {
            delete input.dataset.editMessage;
            delete input.dataset.removedAttachments;
            delete input.dataset.originalMessageText;
            input.value = "";
            input.style.backgroundColor = '#303030';
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
        const input = this.getMessageInput();
        if (input) input.value = "";
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

    updateMobileLayout() {
        if (window.innerWidth >= 768) return;
        const vvHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
        const offsetTop = window.visualViewport ? window.visualViewport.offsetTop : 0;
        const controls = document.querySelector('#room .chat-controls');
        const controlsHeight = controls ? controls.offsetHeight : 50;
        const messagesHeight = vvHeight - 50 - controlsHeight;
        document.documentElement.style.setProperty('--messages-height', `${messagesHeight}px`);
        const header = document.querySelector('.folded-room-header');
        if (header) header.style.top = `${offsetTop}px`;
    }
}
