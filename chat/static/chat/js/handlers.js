import {
    onSubmitMessage,
    onUpdateVote,
    onRoomTryLeave,
    onRoomTryJoin,
    onToggleNotifications,
    onMessageHistory,
    onReceiveMessages,
    onRoomUnsee,
    onReceiveVotes,
    onReceiveEdit,
    onReceiveOnlineUpdates,
    onReceiveNotification,
    copyRoomLink,
    copyMessageLink,
} from './chat.js';

import DomApi from './domapi.js';

const DOM_API = new DomApi();

export async function onSocketMessage(data) {
    if (data.join) {
        console.warn("deprecated");
    } else if (data.leave) {
        console.warn("deprecated");
    } else if (data.messages) {
        onReceiveMessages(data.messages);
    } else if (data.unsee_room) {
        onRoomUnsee(data.unsee_room);
    } else if (data.notification) {
        let notif = data.notification
        onReceiveNotification(notif);
    } else if (data.update_votes) {
        let event = data.update_votes;
        onReceiveVotes(event);
    } else if (data.edit_message) {
        let edit = data.edit_message;
        onReceiveEdit(edit);
    } else if (data.online_data) {
        onReceiveOnlineUpdates(data.online_data);
    } else {
        console.log("Cannot handle message!");
    }
}

// Hook up send button to send a message
$(document).on("click", ".send-message", function() {
    let edit_message_id = DOM_API.getEditedMessageId();
    let message = DOM_API.getEnteredText();
    onSubmitMessage(message, edit_message_id);
});

$(document).on("keydown", "#message-input", function(e) {
    if (e.keyCode == 13) {
        let edit_message_id = DOM_API.getEditedMessageId();
        let message = DOM_API.getEnteredText();
        onSubmitMessage(message, edit_message_id);
    }

    if (e.key == "ArrowUp") {
        // up arrow will move caret to start by default
        e.preventDefault();
        let message = DOM_API.getLatestOwnMessage();
        let message_id = message.data('message-id');
        if (!DOM_API.isEditing()) {
            DOM_API.setEditing(message_id);
        }
    }
});

$(document).on('click', '.attachment-image-container', function(e) {
    let srcs = []
    for (let img of $(this).find("img")) {
        srcs.push(img.src);
    }
    DOM_API.openBigImage(srcs);
});

$(document).on('click', '.notif-switch', function() {
    const $btn = $(this);
    const currentState = $btn.data("enabled") === "true" || $btn.data("enabled") === true;
    const newState = !currentState;
    
    // Update UI immediately for instant feedback
    $btn.data("enabled", newState);
    const $icon = $btn.find("i");
    if (newState) {
        $icon.removeClass("fa-bell-slash").addClass("fa-bell");
    } else {
        $icon.removeClass("fa-bell").addClass("fa-bell-slash");
    }
    
    onToggleNotifications($btn.data("room-id"), newState);
});

$(document).on('keydown', function(e) {
    if (e.key !== "Escape") {
        return;
    }

    if (!DOM_API.isEditing()) {
        return;
    }

    DOM_API.stopEditing();
});

// $(document).on('click', ".stop-editing", function(e) {
//     DOM_API.stopEditing();
// });

$(document).on('click', ".delete-images-preview", function(e) {
    let room_id = $(this).data("room-id");
    DOM_API.clearFiles(room_id);
});

$(document).on('click', '.copy-room-url', function(e) {
    e.preventDefault();
    e.stopPropagation();
    let room_id = $(this).data('room-id');
    copyRoomLink(room_id, this);
});

$(document).on('click', '.copy-message-url', function(e) {
    e.preventDefault();
    e.stopPropagation();
    let room_id = $(this).data('room-id');
    let message_id = $(this).data('message-id');
    copyMessageLink(room_id, message_id, this);
});

$(document).on("change", ".file-input", function(e) {
    let files = this.files;
    let preview_container = DOM_API.getPreviewDiv();
    
    // If editing, keep existing attachments and append new ones
    if (!DOM_API.isEditing()) {
        preview_container.empty();
    }

    if (files.length > 0) {
        DOM_API.getPreviewContainer().show();
    }

    for (let i = 0; i < files.length; ++i) {
        let file = files.item(i);
        let fr = new FileReader();

        let preview_id = `preview-new-${i}-${Date.now()}`;

        let img_html = `<div class="image-preview-wrapper" style="position: relative; display: inline-block;">
            <img class='image-preview new-attachment' id='${preview_id}'>
            <button class="btn btn-sm btn-danger remove-new-attachment" 
                style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 12px;"
                data-preview-id="${preview_id}" type="button">×</button>
        </div>`;
        preview_container.append(img_html);
        
        fr.onload = function(e) {
            $(`#${preview_id}`)[0].src = this.result;
        };

        fr.readAsDataURL(file);
    }
});

// Vote button handler
$(document).on("click", ".msg-vote", function() {
    let event_type = $(this).data("event-name"); // upvote / downvote
    let message_id = $(this).data("message-id");

    // if is active and pressed it means vote has to be removed
    let is_add = !$(this).hasClass('active');

    onUpdateVote(event_type, message_id, is_add);
});

// Show history handler
$(document).on("click", ".show-history", async function() {
    let message_id = $(this).data('message-id');
    onMessageHistory(message_id);
});

// Edit button handler
$(document).on("click", ".edit-message", function() {
    let message_id = $(this).data("message-id");
    DOM_API.setEditing(message_id);
});

// Remove existing attachment during editing
$(document).on("click", ".remove-existing-attachment", function(e) {
    e.preventDefault();
    e.stopPropagation();
    let filename = $(this).data("filename");
    DOM_API.addRemovedAttachment(filename);
    $(this).closest('.image-preview-wrapper').remove();
    
    // Hide preview container if no images left
    if (DOM_API.getPreviewDiv().children().length === 0) {
        DOM_API.getPreviewContainer().hide();
    }
});

// Remove new attachment during editing (before upload)
$(document).on("click", ".remove-new-attachment", function(e) {
    e.preventDefault();
    e.stopPropagation();
    $(this).closest('.image-preview-wrapper').remove();
    
    // Clear file input if no new attachments left
    if (DOM_API.getPreviewDiv().find('.new-attachment').length === 0) {
        DOM_API.getFileInput().val("");
    }
    
    // Hide preview container if no images left
    if (DOM_API.getPreviewDiv().children().length === 0) {
        DOM_API.getPreviewContainer().hide();
    }
});

// Room join/leave - using event delegation for better mobile support
$(document).on('click touchstart', '.room-name', function(e) {
    // Prevent default to avoid double-tap zoom on mobile
    if (e.type === 'touchstart') {
        e.preventDefault();
    }
    
    let room_id = $(this).parent().attr("data-room-id");

    if ($(this).hasClass("joined")) {
        // ignore second click on active room
        //onRoomTryLeave(true);
    } else {
        // Add visual feedback immediately
        $(this).parent().addClass('room-tapping');
        // Remove feedback after a short delay
        setTimeout(() => {
            $(this).parent().removeClass('room-tapping');
        }, 300);
        
        // Join room
        onRoomTryJoin(room_id);
    }
});

$(document).on('click', '.enable-notifications-btn', async function(e) {
    e.preventDefault();
    try {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            location.reload();
        }
    } catch (error) {
        console.error('Error requesting notification permission:', error);
    }
});

$(function() {
    if (!Notification) {
        return;
    }

    if (Notification.permission !== 'granted') {
        DOM_API.addPermissionBanner();
    }
    // if (Notification.permission !== 'granted' && localStorage.notifications !== "No") {
    //     DOM_API.addPermissionBanner();
    // }

})