/**
 * @file
 * DOM API module providing a clean interface for DOM manipulation operations.
 * Handles all UI updates, element queries, and DOM-related functionality for the chat application.
 */

import {
    removeNotification,
    formatTime,
    escapeHtml,
    getImageSize,
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
    /**
     * Gets the room link element for a given room ID
     * @param {number} room_id - The room ID
     * @returns {Element|null}
     */
    getRoomLinkDiv(room_id) {
        return $(`.room-link[data-room-id="${room_id}"]`);
    }

    /**
     * Creates the room div and appends it to the messages container
     * @param {number} room_id - The room ID
     * @param {string} title - The room title
     * @param {boolean} is_public - Whether the room is public
     * @param {boolean} notifs_enabled - Whether notifications are enabled for this room
     * @returns {Element}
     */
    createRoomDiv(room_id, title, is_public, notifs_enabled) {
        const html = Room({ room_id, title, is_public, notifs_enabled });
        const container = $('.chat-root-messages');
        container.innerHTML = '';
        container.insertAdjacentHTML('beforeend', html);
        return container.firstElementChild;
    }

    /**
     * Gets the main room container element
     * @returns {Element|null}
     */
    getRoom() {
        return $('#room');
    }

    /**
     * Gets the messages container within the room
     * @returns {Element|null}
     */
    getMessagesDiv() {
        const room = this.getRoom();
        return room ? $('.messages', room) : null;
    }

    /**
     * Adds a message to the chat display
     * @param {number} room_id - Room ID
     * @param {number} message_id - Unique message ID
     * @param {string} username - Sender's username
     * @param {string} message - Message content
     * @param {number} upvotes - Upvote count
     * @param {number} downvotes - Downvote count
     * @param {string|null} vote - Current user's vote ('upvote', 'downvote', or null)
     * @param {boolean} own - Whether message was sent by current user
     * @param {boolean} edited - Whether message has been edited
     * @param {Object} [attachments] - Attachment data with images array
     * @param {number} original_ts - Original message timestamp
     * @param {number} latest_ts - Latest timestamp (for edited messages)
     */
    addMessage(room_id, message_id,
        username, message,
        upvotes, downvotes, vote,
        own, edited,
        attachments,
        original_ts, latest_ts) {

        let type = this.getRoomType(room_id);

        let html = Message({
            room_id,
            message_id,
            username,
            message: this.formatMessage(message),
            upvotes,
            downvotes,
            vote,
            own,
            edited,
            attachments,
            original_ts,
            latest_ts: formatTime(latest_ts),
            type,
        });

        const messagesDiv = this.getMessagesDiv();
        if (messagesDiv) {
            messagesDiv.insertAdjacentHTML('beforeend', html);
        }

        // make own vote appear active
        const voteDiv = this.getVoteDiv(message_id, vote);
        if (voteDiv) {
            voteDiv.classList.add('active');
        }
    }

    /**
     * Adds a date banner to the messages container
     * @param {string} text - Text to display in the banner
     */
    addDateBanner(text) {
        const messagesDiv = this.getMessagesDiv();
        if (messagesDiv) {
            messagesDiv.insertAdjacentHTML('beforeend', `<div>${text}</div>`);
        }
    }

    /**
     * Gets the message element for a given message ID
     * @param {number} message_id - The message ID
     * @returns {Element|null}
     */
    getMessageDiv(message_id) {
        return $(`.message[data-message-id="${message_id}"]`);
    }

    /**
     * Scrolls to a specific message in the chat
     * @param {number} message_id - The message ID to scroll to
     * @returns {boolean} - true if message was found and scrolled to, false otherwise
     */
    scrollToMessage(message_id) {
        let message = this.getMessageDiv(message_id);
        if (!message) {
            return false;
        }
        message.scrollIntoView();

        message.classList.add('msg-highlight');
        setTimeout(() => message.classList.remove('msg-highlight'), 5000);
        return true;
    }

    /**
     * Gets the upvote count element for a message
     * @param {number} message_id - The message ID
     * @returns {Element|null}
     */
    getMessageUpvotesCountDiv(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? $(".msg-upvotes", msgDiv) : null;
    }

    /**
     * Gets the downvote count element for a message
     * @param {number} message_id - The message ID
     * @returns {Element|null}
     */
    getMessageDownvotesCountDiv(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? $(".msg-downvotes", msgDiv) : null;
    }

    /**
     * Gets the vote button element for a message and vote type
     * @param {number} message_id - The message ID
     * @param {string} vote - Vote type ('upvote' or 'downvote')
     * @returns {Element|null}
     */
    getVoteDiv(message_id, vote) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? $(`.msg-vote[data-event-name="${vote}"]`, msgDiv) : null;
    }

    /**
     * Updates the text of an edited message
     * @param {number} message_id - The message ID
     * @param {string} text - New message text
     * @param {number} ts - Timestamp to display
     * @returns {Element|null}
     */
    editMessageText(message_id, text, ts) {
        let f = this.formatMessage(text);
        let time = formatTime(ts);
        const timeDiv = this.getMessageTimeDiv(message_id);
        if (timeDiv) {
            timeDiv.textContent = time;
        }
        const msgDiv = this.getMessageDiv(message_id);
        if (msgDiv) {
            const msgText = $(".msg-text", msgDiv);
            if (msgText) {
                msgText.innerHTML = f;
                return msgText;
            }
        }
        return null;
    }

    /**
     * Updates message attachments (for editing)
     * @param {number} message_id - The message ID
     * @param {Object} attachments - Attachment data with images array
     */
    updateMessageAttachments(message_id, attachments) {
        let message_div = this.getMessageDiv(message_id);
        if (!message_div) return;
        let attachment_container = $('.attachment-image-container', message_div);
        if (attachment_container) {
            attachment_container.innerHTML = '';

            if (attachments && attachments.images && attachments.images.length > 0) {
                for (let filename of attachments.images) {
                    attachment_container.insertAdjacentHTML('beforeend', `<img class='attached-image' src='/media/uploads/${filename}'>`);
                }
            }
        }
    }

    /**
     * Shows the edit history button for a message
     * @param {number} message_id - The message ID
     */
    showHistoryButton(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        if (msgDiv) {
            const btn = $(".show-history", msgDiv);
            if (btn) {
                btn.style.display = '';
            }
        }
    }

    /**
     * Gets the room type for a given room ID
     * @param {number} room_id - The room ID
     * @returns {string|null}
     */
    getRoomType(room_id) {
        const el = $(`.room-link[data-room-id="${room_id}"]`);
        return el ? el.getAttribute("data-room-type") : null;
    }

    /**
     * Gets all date banner elements in the messages container
     * @returns {NodeList}
     */
    getLastMessageBanner() {
        const messagesDiv = this.getMessagesDiv();
        return messagesDiv ? $$('.date-banner', messagesDiv) : [];
    }

    /**
     * Gets the text content of a message
     * @param {number} message_id - The message ID
     * @returns {string}
     */
    getMessageText(message_id) {
        const msgDiv = this.getMessageDiv(message_id);
        return msgDiv ? ($(".msg-text", msgDiv) || {}).textContent || '' : '';
    }

    /**
     * Formats a message by escaping HTML and converting URLs to links
     * @param {string} raw_message - Raw message text
     * @returns {string}
     */
    formatMessage(raw_message) {
        let escaped = escapeHtml(raw_message);
        let URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)/g;
        let formatted = escaped;

        let matches = escaped.match(URL_REGEX);
        if (matches != null) {
            for (let match of matches) {
                formatted = raw_message.replace(match, `<a href='${match}' target="_blank">${match}</a>`);
            }
        }
        return formatted;
    }

    /**
     * Gets the image preview container
     * @returns {Element|null}
     */
    getPreviewDiv() {
        return $(".preview-images");
    }

    /**
     * Gets the image preview container (with close button)
     * @returns {Element|null}
     */
    getPreviewContainer() {
        return $(`.image-preview-container`);
    }

    /**
     * Marks a room as seen (removes unread indicator)
     * @param {number} room_id - The room ID
     */
    seenChat(room_id) {
        let room_link = this.getRoomLinkDiv(room_id);
        if (room_link) {
            room_link.classList.remove("room-not-seen");
        }

        // all rooms are seen, change tab icon back
        if ($$('.room-not-seen').length === 0) {
            removeNotification();
        }
    }

    /**
     * Updates online status indicator for a room
     * @param {number} room_id - The room ID
     * @param {boolean} is_online - Whether the room is online
     */
    updateOnline(room_id, is_online) {
        let room_link = this.getRoomLinkDiv(room_id);
        if (!room_link) return;
        if (is_online) {
            room_link.classList.remove('offline');
            room_link.classList.add('online');
        } else {
            room_link.classList.remove('online');
            room_link.classList.add('offline');
        }
    }

    /**
     * Gets the timestamp element for a message
     * @param {number} message_id - The message ID
     * @returns {Element|null}
     */
    getMessageTimeDiv(message_id) {
        return $(`.message-timestamp[data-message-id=${message_id}]`);
    }

    /**
     * Gets the message input field
     * @returns {Element|null}
     */
    getMessageInput() {
        return $(`#message-input`);
    }

    /**
     * Gets the current text in the message input
     * @returns {string}
     */
    getEnteredText() {
        const input = this.getMessageInput();
        return input ? input.value : '';
    }

    /**
     * Gets the anonymous mode checkbox state
     * @returns {boolean}
     */
    getAnonymousValue() {
        const el = $(`.anonymous-switch`);
        return el ? el.checked : false;
    }

    /**
     * Gets the file input element
     * @returns {Element|null}
     */
    getFileInput() {
        return $(`#file-input`);
    }

    /**
     * Gets the selected files from the file input
     * @returns {FileList}
     */
    getFiles() {
        const input = this.getFileInput();
        return input ? input.files : null;
    }

    /**
     * Clears file input and preview containers
     */
    clearFiles() {
        const fileInput = $(`#file-input`);
        if (fileInput) {
            fileInput.value = "";
        }
        this.getPreviewContainer().style.display = 'none';
        const previewDiv = this.getPreviewDiv();
        if (previewDiv) {
            previewDiv.innerHTML = '';
        }
        // Don't clear removed-attachments data here, it's needed for editing
    }

    /**
     * Gets the currently edited message ID from input data
     * @returns {number|null}
     */
    getEditedMessageId() {
        const input = this.getMessageInput();
        return input ? input.dataset.editMessage : null;
    }

    /**
     * Sets editing mode for a message
     * @param {number} message_id - The message ID to edit
     */
    setEditing(message_id) {
        let text = this.getMessageText(message_id);
        const fileInput = this.getFileInput();
        if (fileInput) {
            fileInput.removeAttribute('disabled');
        }
        const input = this.getMessageInput();
        if (input) {
            input.dataset.editMessage = message_id;
            input.dataset.originalMessageText = text;
            input.value = text;
            input.style.backgroundColor = '#4a4a00';
        }

        // Load existing attachments for editing
        let attachments = this.getMessageAttachments(message_id);
        this.loadEditingAttachments(message_id, attachments);

        const inputEl = this.getMessageInput();
        if (inputEl) {
            setCaretPosition(inputEl, text.length);
        }
    }

    /**
     * Stops editing mode and clears input
     */
    stopEditing() {
        const fileInput = this.getFileInput();
        if (fileInput) {
            fileInput.removeAttribute('disabled');
        }
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

    /**
     * Opens an image in a PhotoSwipe lightbox
     * @param {Array<string>} srcs - Array of image URLs to display
     * @returns {Promise<void>}
     */
    async openBigImage(srcs) {
        let pswpElement = $$('.pswp')[0];
        let items = [];
        for (let src of srcs) {
            let size = await getImageSize(src);
            items.push({
                src,
                w: size.w,
                h: size.h
            });
        }
        let gallery = new PhotoSwipe(pswpElement, PhotoSwipeUI_Default, items, {
            index: 0, // start at first slide
            closeOnScroll: false,
        });
        gallery.init();
    }

    /**
     * Closes the PhotoSwipe lightbox
     */
    closeBigImage() {
        const el = $("#big-image");
        if (el) {
            el.remove();
        }
        document.body.classList.remove('modal-open');
    }

    /**
     * Gets the most recent message sent by the current user
     * @returns {Element|null}
     */
    getLatestOwnMessage() {
        const messagesDiv = this.getMessagesDiv();
        if (!messagesDiv) return null;
        const ownMessages = $$('.message.own', messagesDiv);
        return ownMessages.length > 0 ? ownMessages[ownMessages.length - 1] : null;
    }

    /**
     * Checks if currently editing a message
     * @returns {boolean}
     */
    isEditing() {
        return this.getEditedMessageId() ? true : false;
    }

    /**
     * Removes the "empty chat" banner
     */
    removeNoMessagesBanner() {
        const banner = $('.empty-chat-message');
        if (banner) {
            banner.remove();
        }
    }

    /**
     * Sets the room title in the UI
     * @param {string} title - The room title to set
     */
    setRoomTitle(title) {
        const el = $("#room-title");
        if (el) {
            el.textContent = title;
        }
    }

    /**
     * Sets the notification toggle state for a room
     * @param {number} room_id - The room ID
     * @param {boolean} is_enabled - Whether notifications are enabled
     */
    setRoomNotifications(room_id, is_enabled) {
        const btn = $(`.notif-switch[data-room-id='${room_id}']`);
        if (!btn) return;
        btn.disabled = false;
        btn.dataset.enabled = is_enabled;

        // Update icon: bell if enabled, bell-slash if disabled
        const icon = $("i", btn);
        if (icon) {
            if (is_enabled) {
                icon.classList.remove("fa-bell-slash");
                icon.classList.add("fa-bell");
            } else {
                icon.classList.remove("fa-bell");
                icon.classList.add("fa-bell-slash");
            }
        }
    }

    /**
     * Clears all room data from the UI
     */
    clearRoomData() {
        const messagesDiv = this.getMessagesDiv();
        if (messagesDiv) {
            messagesDiv.innerHTML = '';
        }
        const input = this.getMessageInput();
        if (input) {
            input.value = "";
        }
        this.clearFiles();
        this.stopEditing();
        if (messagesDiv) {
            messagesDiv.insertAdjacentHTML(
                'beforeend',
                "<p class='empty-chat-message'>" + _("Loading...") + "</p>"
            );
        }
    }

    /**
     * Shows visual feedback after a copy operation
     * @param {HTMLElement} button - The button element
     * @param {string} message - Feedback message
     * @param {boolean} success - Whether the operation succeeded
     */
    showCopyFeedback(button, message, success) {
        if (!button) {
            return;
        }

        let $tooltip = document.createElement('span');
        $tooltip.className = "copy-feedback badge";
        $tooltip.textContent = message;
        $tooltip.classList.add(success ? 'text-bg-success' : 'text-bg-danger');

        button.appendChild($tooltip);
        setTimeout(() => {
            $tooltip.style.transition = 'opacity 0.2s';
            $tooltip.style.opacity = '0';
            setTimeout(() => {
                if ($tooltip.parentNode) {
                    $tooltip.remove();
                }
            }, 200);
        }, 1200);
    }

    /**
     * Gets current attachments from a message element
     * @param {number} message_id - The message ID
     * @returns {Object}
     */
    getMessageAttachments(message_id) {
        let message_div = this.getMessageDiv(message_id);
        let attachments = { images: [] };
        if (message_div) {
            const images = $$('.attached-image', message_div);
            images.forEach(function(img) {
                let src = img.getAttribute('src');
                let filename = src.split('/').pop();
                attachments.images.push(filename);
            });
        }
        return attachments.images.length > 0 ? attachments : {};
    }

    /**
     * Loads existing attachments into the preview area during editing
     * @param {number} message_id - The message ID
     * @param {Object} attachments - Attachment data with images array
     */
    loadEditingAttachments(message_id, attachments) {
        let preview_container = this.getPreviewDiv();
        if (preview_container) {
            preview_container.innerHTML = '';
        }

        if (!attachments || !attachments.images || attachments.images.length === 0) {
            const container = this.getPreviewContainer();
            if (container) {
                container.style.display = 'none';
            }
            return;
        }

        const container = this.getPreviewContainer();
        if (container) {
            container.style.display = '';
        }

        for (let i = 0; i < attachments.images.length; i++) {
            let filename = attachments.images[i];
            let preview_id = `preview-existing-${i}`;
            let img_html = `<div class="image-preview-wrapper" style="position: relative; display: inline-block;">
                <img class='image-preview' id='${preview_id}' src='/media/uploads/${filename}' data-filename='${filename}'>
                <button class="btn btn-sm btn-danger remove-existing-attachment"
                    style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 12px;"
                    data-filename="${filename}" type="button">×</button>
            </div>`;
            if (preview_container) {
                preview_container.insertAdjacentHTML('beforeend', img_html);
            }
        }
    }

    /**
     * Gets the list of removed attachment filenames from input data
     * @returns {Array<string>}
     */
    getRemovedAttachments() {
        const input = this.getMessageInput();
        return input ? (input.dataset.removedAttachments ? JSON.parse(input.dataset.removedAttachments) : []) : [];
    }

    /**
     * Adds a filename to the removed attachments list
     * @param {string} filename - The filename to mark as removed
     */
    addRemovedAttachment(filename) {
        let removed = this.getRemovedAttachments();
        if (!removed.includes(filename)) {
            removed.push(filename);
            const input = this.getMessageInput();
            if (input) {
                input.dataset.removedAttachments = JSON.stringify(removed);
            }
        }
    }

    /**
     * Gets the original message text from input data
     * @param {number} message_id - The message ID
     * @returns {string}
     */
    getOriginalMessageText(message_id) {
        const input = this.getMessageInput();
        return input ? input.dataset.originalMessageText : '';
    }
}