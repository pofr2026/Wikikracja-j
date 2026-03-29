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
    setCaretPosition
} from './utility.js';
import { Room, Message } from './templates.js';

/**
 * DOM API class for managing chat interface DOM operations
 * @class
 */
export default class DomApi {
    /**
     * Gets the jQuery-wrapped room link element for a given room ID
     * @param {number} room_id - The room ID
     * @returns {jQuery} - jQuery object containing the room link element
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
     * @returns {jQuery} - jQuery object containing the created room div
     */
    createRoomDiv(room_id, title, is_public, notifs_enabled) {
        let roomdiv = $(Room({ room_id, title, is_public, notifs_enabled }));
        $(".chat-root-messages").empty().append(roomdiv);
        return roomdiv;
    }

    /**
     * Gets the main room container element
     * @returns {jQuery} - jQuery object containing the #room element
     */
    getRoom() {
        return $(`#room`)
    }

    /**
     * Gets the messages container within the room
     * @returns {jQuery} - jQuery object containing the messages div
     */
    getMessagesDiv() {
        return this.getRoom().find('.messages');
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

        this.getMessagesDiv().append(html);

        // make own vote appear active
        this.getVoteDiv(message_id, vote).addClass('active');
    }

    /**
     * Adds a date banner to the messages container
     * @param {string} text - Text to display in the banner
     */
    addDateBanner(text) {
        this.getMessagesDiv().append(`<div>${text}</div>`)
    }

    /**
     * Gets the message element for a given message ID
     * @param {number} message_id - The message ID
     * @returns {jQuery} - jQuery object containing the message element
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
        if (!message.length) {
            return false;
        }
        message[0].scrollIntoView();

        message.addClass('msg-highlight');
        setTimeout(() => message.removeClass('msg-highlight'), 5000);
        return true;
    }

    /**
     * Gets the upvote count element for a message
     * @param {number} message_id - The message ID
     * @returns {jQuery} - jQuery object containing the upvote count
     */
    getMessageUpvotesCountDiv(message_id) {
        return this.getMessageDiv(message_id).find(".msg-upvotes");
    }

    /**
     * Gets the downvote count element for a message
     * @param {number} message_id - The message ID
     * @returns {jQuery} - jQuery object containing the downvote count
     */
    getMessageDownvotesCountDiv(message_id) {
        return this.getMessageDiv(message_id).find(".msg-downvotes");
    }

    /**
     * Gets the vote button element for a message and vote type
     * @param {number} message_id - The message ID
     * @param {string} vote - Vote type ('upvote' or 'downvote')
     * @returns {jQuery} - jQuery object containing the vote button
     */
    getVoteDiv(message_id, vote) {
        return this.getMessageDiv(message_id).find(`.msg-vote[data-event-name="${vote}"]`)
    }

    /**
     * Updates the text of an edited message
     * @param {number} message_id - The message ID
     * @param {string} text - New message text
     * @param {number} ts - Timestamp to display
     * @returns {jQuery} - jQuery object containing the message text element
     */
    editMessageText(message_id, text, ts) {
        let f = this.formatMessage(text)
        let time = formatTime(ts);
        this.getMessageTimeDiv(message_id).text(time);
        return this.getMessageDiv(message_id).find(".msg-text").html(f);
    }

    /**
     * Updates message attachments (for editing)
     * @param {number} message_id - The message ID
     * @param {Object} attachments - Attachment data with images array
     */
    updateMessageAttachments(message_id, attachments) {
        let message_div = this.getMessageDiv(message_id);
        let attachment_container = message_div.find('.attachment-image-container');
        attachment_container.empty();
        
        if (attachments && attachments.images && attachments.images.length > 0) {
            for (let filename of attachments.images) {
                attachment_container.append(`<img class='attached-image' src='/media/uploads/${filename}'>`);
            }
        }
    }

    /**
     * Shows the edit history button for a message
     * @param {number} message_id - The message ID
     */
    showHistoryButton(message_id) {
        this.getMessageDiv(message_id).find(".show-history").show();
    }

    /**
     * Gets the room type for a given room ID
     * @param {number} room_id - The room ID
     * @returns {string} - Room type (e.g., 'public', 'private')
     */
    getRoomType(room_id) {
        return $(`.room-link[data-room-id="${room_id}"]`).attr("data-room-type");
    }

    /**
     * Gets all date banner elements in the messages container
     * @returns {jQuery} - jQuery object containing date banners
     */
    getLastMessageBanner() {
        return this.getMessagesDiv().find('.date-banner');
    }

    /**
     * Gets the text content of a message
     * @param {number} message_id - The message ID
     * @returns {string} - Message text content
     */
    getMessageText(message_id) {
        return this.getMessageDiv(message_id).find(".msg-text").text();
    }

    /**
     * Formats a message by escaping HTML and converting URLs to links
     * @param {string} raw_message - Raw message text
     * @returns {string} - Formatted HTML-safe message text
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
     * @returns {jQuery} - jQuery object containing the preview container
     */
    getPreviewDiv() {
        return $(".preview-images")
    }

    /**
     * Gets the image preview container (with close button)
     * @returns {jQuery} - jQuery object containing the preview container
     */
    getPreviewContainer() {
        return $(`.image-preview-container`)
    }

    /**
     * Marks a room as seen (removes unread indicator)
     * @param {number} room_id - The room ID
     */
    seenChat(room_id) {
        let room_link = this.getRoomLinkDiv(room_id);
        room_link.removeClass("room-not-seen");

        // all rooms are seen, change tab icon back
        if ($('.room-not-seen').length == 0) {
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
        if (is_online) {
            room_link.removeClass('offline').addClass('online');
        } else {
            room_link.removeClass('online').addClass('offline');
        }
    }

    /**
     * Gets the timestamp element for a message
     * @param {number} message_id - The message ID
     * @returns {jQuery} - jQuery object containing the timestamp element
     */
    getMessageTimeDiv(message_id) {
        return $(`.message-timestamp[data-message-id=${message_id}]`);
    }

    /**
     * Gets the message input field
     * @returns {jQuery} - jQuery object containing the message input
     */
    getMessageInput() {
        return $(`#message-input`);
    }

    /**
     * Gets the current text in the message input
     * @returns {string} - Current input value
     */
    getEnteredText() {
        return this.getMessageInput().val();
    }

    /**
     * Gets the anonymous mode checkbox state
     * @returns {boolean} - Whether anonymous mode is enabled
     */
    getAnonymousValue() {
        return $(`.anonymous-switch`).is(":checked");
    }

    /**
     * Gets the file input element
     * @returns {jQuery} - jQuery object containing the file input
     */
    getFileInput() {
        return $(`#file-input`);
    }

    /**
     * Gets the selected files from the file input
     * @returns {FileList} - List of selected files
     */
    getFiles() {
        return this.getFileInput()[0].files;
    }

    /**
     * Clears file input and preview containers
     */
    clearFiles() {
        $(`#file-input`).val("");
        this.getPreviewContainer().hide();
        this.getPreviewDiv().empty();
        // Don't clear removed-attachments data here, it's needed for editing
    }

    /**
     * Gets the currently edited message ID from input data
     * @returns {number|null} - The message ID being edited, or null
     */
    getEditedMessageId() {
        return this.getMessageInput().data('edit-message');
    }

    /**
     * Sets editing mode for a message
     * @param {number} message_id - The message ID to edit
     */
    setEditing(message_id) {
        let text = this.getMessageText(message_id);
        this.getFileInput().removeAttr('disabled');
        this.getMessageInput().data('edit-message', message_id)
            .data('original-message-text', text)
            .val(text)
            .css('background-color', '#4a4a00');
        
        // Load existing attachments for editing
        let attachments = this.getMessageAttachments(message_id);
        this.loadEditingAttachments(message_id, attachments);
        
        setCaretPosition(this.getMessageInput()[0], text.length);
    }

    /**
     * Stops editing mode and clears input
     */
    stopEditing() {
        this.getFileInput().removeAttr('disabled');
        this.getMessageInput().removeData('edit-message')
            .removeData('removed-attachments')
            .removeData('original-message-text')
            .val("")
            .css('background-color', '#303030');
        this.clearFiles();
    }

    /**
     * Opens an image in a PhotoSwipe lightbox
     * @param {Array<string>} srcs - Array of image URLs to display
     * @returns {Promise<void>}
     */
    async openBigImage(srcs) {
        let pswpElement = document.querySelectorAll('.pswp')[0];
        let items = [];
        for (let src of srcs) {
            let size = await getImageSize(src);
            items.push({
                src,
                w: size.w,
                h: size.h
            })
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
        $("#big-image").remove();
        $('body').removeClass('modal-open');
    }

    /**
     * Gets the most recent message sent by the current user
     * @returns {jQuery} - jQuery object containing the message element
     */
    getLatestOwnMessage() {
        return this.getMessagesDiv().find('.message.own').last();
    }

    /**
     * Checks if currently editing a message
     * @returns {boolean} - true if editing, false otherwise
     */
    isEditing() {
        return this.getEditedMessageId() ? true : false;
    }

    /**
     * Removes the "empty chat" banner
     */
    removeNoMessagesBanner() {
        $('.empty-chat-message').remove();
    }

    /**
     * Sets the room title in the UI
     * @param {string} title - The room title to set
     */
    setRoomTitle(title) {
        $("#room-title").text(title);
    }

    /**
     * Sets the notification toggle state for a room
     * @param {number} room_id - The room ID
     * @param {boolean} is_enabled - Whether notifications are enabled
     */
    setRoomNotifications(room_id, is_enabled) {
        const $btn = $(".notif-switch[data-room-id='" + room_id + "']");
        $btn.prop("disabled", false);
        $btn.data("enabled", is_enabled);
        
        // Update icon: bell if enabled, bell-slash if disabled
        const $icon = $btn.find("i");
        if (is_enabled) {
            $icon.removeClass("fa-bell-slash").addClass("fa-bell");
        } else {
            $icon.removeClass("fa-bell").addClass("fa-bell-slash");
        }
    }

    /**
     * Clears all room data from the UI
     */
    clearRoomData() {
        this.getMessagesDiv().empty();
        this.getMessageInput().val("");
        this.clearFiles();
        this.stopEditing();
        this.getMessagesDiv().append(
            "<p class='empty-chat-message'>" + _("Loading...") + "</p>"
        );
    }

    /**
     * Adds a banner prompting user to enable notifications
     */
    addPermissionBanner() {
        $('.chat-page-header').append("<button type='button' class='alert alert-info p-1 m-1 enable-notifications-btn'><i class='far fa-bell-slash'></i> " + _("Click here to enable notifications") + " <i class ='far fa-bell-slash'></i></button>")
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

        let $button = $(button);
        let $tooltip = $('<span class="copy-feedback badge"></span>');
        $tooltip.text(message);
        $tooltip.toggleClass('text-bg-success', !!success);
        $tooltip.toggleClass('text-bg-danger', !success);

        $button.append($tooltip);
        setTimeout(() => {
            $tooltip.fadeOut(200, function () {
                $(this).remove();
            });
        }, 1200);
    }

    /**
     * Gets current attachments from a message element
     * @param {number} message_id - The message ID
     * @returns {Object} - Attachment data with images array
     */
    getMessageAttachments(message_id) {
        let message_div = this.getMessageDiv(message_id);
        let attachments = { images: [] };
        message_div.find('.attached-image').each(function() {
            let src = $(this).attr('src');
            let filename = src.split('/').pop();
            attachments.images.push(filename);
        });
        return attachments.images.length > 0 ? attachments : {};
    }

    /**
     * Loads existing attachments into the preview area during editing
     * @param {number} message_id - The message ID
     * @param {Object} attachments - Attachment data with images array
     */
    loadEditingAttachments(message_id, attachments) {
        let preview_container = this.getPreviewDiv();
        preview_container.empty();
        
        if (!attachments || !attachments.images || attachments.images.length === 0) {
            this.getPreviewContainer().hide();
            return;
        }

        this.getPreviewContainer().show();
        
        for (let i = 0; i < attachments.images.length; i++) {
            let filename = attachments.images[i];
            let preview_id = `preview-existing-${i}`;
            let img_html = `<div class="image-preview-wrapper" style="position: relative; display: inline-block;">
                <img class='image-preview' id='${preview_id}' src='/media/uploads/${filename}' data-filename='${filename}'>
                <button class="btn btn-sm btn-danger remove-existing-attachment" 
                    style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 12px;"
                    data-filename="${filename}" type="button">×</button>
            </div>`;
            preview_container.append(img_html);
        }
    }

    /**
     * Gets the list of removed attachment filenames from input data
     * @returns {Array<string>} - Array of removed attachment filenames
     */
    getRemovedAttachments() {
        return this.getMessageInput().data('removed-attachments') || [];
    }

    /**
     * Adds a filename to the removed attachments list
     * @param {string} filename - The filename to mark as removed
     */
    addRemovedAttachment(filename) {
        let removed = this.getRemovedAttachments();
        if (!removed.includes(filename)) {
            removed.push(filename);
            this.getMessageInput().data('removed-attachments', removed);
        }
    }

    /**
     * Gets the original message text from input data
     * @param {number} message_id - The message ID
     * @returns {string} - Original message text
     */
    getOriginalMessageText(message_id) {
        return this.getMessageInput().data('original-message-text');
    }
}