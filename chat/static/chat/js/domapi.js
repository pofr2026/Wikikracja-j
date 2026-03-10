import {
    removeNotification,
    formatTime,
    escapeHtml,
    getImageSize,
    _,
    setCaretPosition
} from './utility.js';
import { Room, Message, MessageHistory } from './templates.js';


export default class DomApi {
    getRoomLinkDiv(room_id) {
        return $(`.room-link[data-room-id="${room_id}"]`);
    }

    createRoomDiv(room_id, title, is_public, notifs_enabled) {
        let roomdiv = $(Room({ room_id, title, is_public, notifs_enabled }));
        $(".chat-root-messages").empty().append(roomdiv);
        return roomdiv;
    }

    getRoom() {
        return $(`#room`)
    }

    getMessagesDiv() {
        return this.getRoom().find('.messages');
    }

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

    addDateBanner(text) {
        this.getMessagesDiv().append(`<div>${text}</div>`)
    }

    getMessageDiv(message_id) {
        //return document.querySelector(`.message[data-message-id="${message_id}"]`).childNodes;
        return $(`.message[data-message-id="${message_id}"]`);
    }

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

    getMessageUpvotesCountDiv(message_id) {
        return this.getMessageDiv(message_id).find(".msg-upvotes");
    }

    getMessageDownvotesCountDiv(message_id) {
        return this.getMessageDiv(message_id).find(".msg-downvotes");
    }

    getVoteDiv(message_id, vote) {
        return this.getMessageDiv(message_id).find(`.msg-vote[data-event-name="${vote}"]`)
    }

    editMessageText(message_id, text, ts) {
        let f = this.formatMessage(text)
        let time = formatTime(ts);
        this.getMessageTimeDiv(message_id).text(time);
        return this.getMessageDiv(message_id).find(".msg-text").html(f);
    }

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

    showHistoryButton(message_id) {
        this.getMessageDiv(message_id).find(".show-history").show();
    }

    getRoomType(room_id) {
        return $(`.room-link[data-room-id="${room_id}"`).attr("data-room-type");
    }

    getLastMessageBanner() {
        return this.getMessagesDiv().find('.date-banner');
    }

    getMessageText(message_id) {
        return this.getMessageDiv(message_id).find(".msg-text").text();
    }

    formatMessage(raw_message) {
        let escaped = escapeHtml(raw_message);
        // let URL_REGEX = /(http(s){0,1}:\/\/){0,1}[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)/g; //default
        let URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)/g; // http only
        // let URL_REGEX = /[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)/g; // dot is enough
        let formatted = escaped;

        let matches = escaped.match(URL_REGEX);
        if (matches != null) {
            for (let match of matches) {
                formatted = raw_message.replace(match, `<a href='${match}' target="_blank">${match}</a>`);
            }
        }
        return formatted;
    }

    // container for images
    getPreviewDiv() {
        return $(".preview-images")
    }

    // container with all images and close button
    getPreviewContainer() {
        return $(`.image-preview-container`)
    }

    seenChat(room_id) {
        let room_link = this.getRoomLinkDiv(room_id);
        room_link.removeClass("room-not-seen");

        // all rooms are seen, change tab icon back
        if ($('.room-not-seen').length == 0) {
            removeNotification();
        }
    }

    updateOnline(room_id, is_online) {
        let room_link = this.getRoomLinkDiv(room_id);
        if (is_online) {
            room_link.removeClass('offline').addClass('online');
        } else {
            room_link.removeClass('online').addClass('offline');
        }
    }

    getMessageTimeDiv(message_id) {
        return $(`.message-timestamp[data-message-id=${message_id}]`);
    }

    getMessageInput() {
        return $(`#message-input`);
    }

    getEnteredText() {
        return this.getMessageInput().val();
    }

    getAnonymousValue() {
        return $(`.anonymous-switch`).is(":checked");
    }

    getFileInput() {
        return $(`#file-input`);
    }

    getFiles() {
        return this.getFileInput()[0].files;
    }

    clearFiles() {
        $(`#file-input`).val("");
        this.getPreviewContainer().hide();
        this.getPreviewDiv().empty();
        // Don't clear removed-attachments data here, it's needed for editing
    }

    getEditedMessageId() {
        return this.getMessageInput().data('edit-message');
    }


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

    stopEditing() {
        this.getFileInput().removeAttr('disabled');
        this.getMessageInput().removeData('edit-message')
            .removeData('removed-attachments')
            .removeData('original-message-text')
            .val("")
            .css('background-color', '#303030');
        this.clearFiles();
    }

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

    closeBigImage() {
        $("#big-image").remove();
        $('body').removeClass('modal-open');
    }

    getLatestOwnMessage() {
        return this.getMessagesDiv().find('.message.own').last();
    }

    isEditing() {
        return this.getEditedMessageId() ? true : false;
    }

    removeNoMessagesBanner() {
        $('.empty-chat-message').remove();
    }

    setRoomTitle(title) {
        $("#room-title").text(title);
    }

    setRoomNotifications(room_id, is_enabled) {
        $(".notif-switch[data-room-id='" + room_id + "']").prop("disabled", false).prop('checked', is_enabled);
    }

    clearRoomData() {
        this.getMessagesDiv().empty();
        this.getMessageInput().val("");
        this.clearFiles();
        this.stopEditing();
        this.getMessagesDiv().append(
            "<p class='empty-chat-message'>" + _("Loading...") + "</p>"
        );
    }


    addPermissionBanner() {
        $('.chat-page-header').append("<button type='button' class='alert alert-info p-1 m-1' onclick='Notification.requestPermission().then(() => location.reload())'><i class='far fa-bell-slash'></i> " + _("Click here to enable notifications") + " <i class ='far fa-bell-slash'></i></button>")
    }

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

    getRemovedAttachments() {
        return this.getMessageInput().data('removed-attachments') || [];
    }

    addRemovedAttachment(filename) {
        let removed = this.getRemovedAttachments();
        if (!removed.includes(filename)) {
            removed.push(filename);
            this.getMessageInput().data('removed-attachments', removed);
        }
    }

    getOriginalMessageText(message_id) {
        return this.getMessageInput().data('original-message-text');
    }
}