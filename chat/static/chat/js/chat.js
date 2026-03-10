import WsApi from './wsapi.js';
import DomApi from './domapi.js';
import { makeNotification, formatDate, formatTime, formatDateTime, Lock, parseParms, _ } from './utility.js';
import { MessageHistory } from './templates.js';

let WS_API;
let DOM_API;
const RoomLock = new Lock();
let current_room = null;
let pendingMessageId = null;


$(() => {
    WS_API = new WsApi();
    DOM_API = new DomApi();

    WS_API.wsOnConnect = async() => {
        // Request data about who is online
        let response = await WS_API.getOnlineUsers();
        let online = response.online_data;
        for (let user of online) {
            DOM_API.updateOnline(user.room_id, user.online);
        }

        let rooms = await WS_API.getNotificationData();
        for (let room_id of rooms.rooms) {
            DOM_API.setRoomNotifications(room_id, true);
        }

        let room_id;

        if (!room_id && window.location.hash) {

            // Get room ID passed with hash (room was created)
            let hash = window.location.hash.slice(1);
            let obj = parseParms(hash);
            if (obj.room_id) {
                room_id = obj.room_id;
            }
            if (obj.message_id) {
                pendingMessageId = obj.message_id;
            }
        }

        // Get locally stored last room ID
        if (!room_id && localStorage.lastUsedRoomID) {
            room_id = localStorage.lastUsedRoomID;
        }

        // Check if room_id was passed from backend
        if (!room_id && LAST_USED_ROOM_ID) {
            room_id = LAST_USED_ROOM_ID;
        }

        // Find the room with the lowest number if no room_id is set
        if (!room_id) {
            let roomElements = $('.room-link[data-room-id]');
            if (roomElements.length > 0) {
                let roomIds = roomElements.map((_, el) => parseInt($(el).data('room-id'))).get();
                room_id = Math.max(...roomIds);
            }
        }

        if (room_id) {
            onRoomTryJoin(room_id);
        }
    }
});

const slow_mode = {};
const slow_mode_time_left = {};

export async function onReceiveNotification(notification) {
    makeNotification(notification)
}

export async function onRoomTryJoin(room_id) {
    if (RoomLock.locked()) {
        await RoomLock.wait();
    }
    // already in this room
    if (room_id == current_room) {
        return;
    }

    // leave current room
    if (current_room) {
        // only do client stuff, user will leave
        // serverside automatically with join
        await onRoomTryLeave(false);
    }

    DOM_API.getRoomLinkDiv(room_id).addClass("joined");

    // already in the room
    if (current_room == room_id) {
        return;
    }

    // joined another room while awaiting confirmation
    if (current_room) {
        return;
    }

    RoomLock.lock();
    let response = await WS_API.joinRoom(room_id);
    RoomLock.unlock();

    localStorage.lastUsedRoomID = room_id;

    current_room = room_id;
    let title = response.title;
    let has_notifs = response.notifications;
    let is_public = response.public;

    // TODO: send seen confirmation to server after a little while
    DOM_API.seenChat(room_id);
    WS_API.seenRoom(room_id);

    //DOM_API.setRoomTitle(title);
    DOM_API.setRoomNotifications(has_notifs);

    DOM_API.createRoomDiv(
        current_room, title, is_public, has_notifs);

    // Put cursor into inout field
    document.querySelector("#message-input").focus();
}

export async function onRoomTryLeave(sync_with_server) {
    if (RoomLock.locked()) {
        await RoomLock.wait();
    }

    if (sync_with_server) {
        RoomLock.lock();
        await WS_API.leaveRoom(current_room);
        RoomLock.unlock();
    }
    DOM_API.getRoomLinkDiv(current_room).removeClass("joined");
    DOM_API.clearRoomData();

    current_room = null;
}

export async function onReceiveMessages(messages) {
    let room_id = messages[0].room_id;

    // received data for wrong room if message was delayed
    if (room_id != current_room) {
        console.warn("received message for wrong room");
        return;
    }

    let msgdiv = DOM_API.getMessagesDiv();
    DOM_API.removeNoMessagesBanner();

    for (let message of messages) {
        let type = DOM_API.getRoomType(message.room_id);
        let current_banner = formatDate(message.timestamp);
        let banner_div = DOM_API.getLastMessageBanner();
        let previous_banner = banner_div.length ? banner_div.last().text() : null;

        if (previous_banner != current_banner) {
            msgdiv.append(`<div class='date-banner'>${current_banner}</div>`);
        }

        DOM_API.addMessage(
            message.room_id, message.message_id,
            message.username, message.message,
            message.upvotes, message.downvotes, message.your_vote,
            message.own, message.edited, message.attachments,
            message.timestamp, message.latest_timestamp
        );

        if (message.new) {
            // Only show notifications for messages from other users
            if (document.hidden && !message.own) {
                makeNotification({
                    title: message.username,
                    body: message.message
                })
            }
        }
        if (message.your_vote /* You voted for this message e.g. 'upvote' or 'downvote' */ ) {
            // find message div and make button appear active
            let active_btn = DOM_API.getVoteDiv(message.message_id, message.your_vote);
            active_btn.addClass('active');
        }
    }

    let shouldStickToBottom = !pendingMessageId;
    if (pendingMessageId) {
        let didScroll = DOM_API.scrollToMessage(pendingMessageId);
        if (didScroll) {
            shouldStickToBottom = false;
        }
        if (didScroll) {
            pendingMessageId = null;
        }
    }

    if (shouldStickToBottom) {
        msgdiv.scrollTop(msgdiv.prop("scrollHeight"));
    }
    document.querySelector("#message-input").focus();
}

export async function onReceiveVotes(event) {
    // find message on page by id and update counters
    let message_div = DOM_API.getMessageDiv(event.message_id);

    DOM_API.getMessageUpvotesCountDiv(event.message_id).text(event.upvotes);
    DOM_API.getMessageDownvotesCountDiv(event.message_id).text(event.downvotes);

    if (event.your_vote /* vote type e.g. upvote or downvote or null if it wasn't you who triggered */ ) {
        // find vote button you pressed
        let active_btn = DOM_API.getVoteDiv(event.message_id, event.your_vote);
        // make all vote buttons appear incative
        message_div.find('.msg-vote').removeClass('active');

        // vote was added
        if (event.add) {
            active_btn.addClass('active');
        } /* vote was removed */
        else {
            // do nothing, all buttons are inactive
        }
    }
}

export async function onReceiveEdit(edit_info) {
    // update text of message
    DOM_API.editMessageText(edit_info.message_id, edit_info.text, edit_info.timestamp);
    
    // update attachments if provided
    if (edit_info.attachments !== undefined) {
        DOM_API.updateMessageAttachments(edit_info.message_id, edit_info.attachments);
    }
    
    //show history button
    DOM_API.showHistoryButton(edit_info.message_id);
}

export async function onReceiveOnlineUpdates(updates) {
    for (let update of updates) {
        DOM_API.updateOnline(update.room_id, update.online);
    }
};

export async function onRoomUnsee(room_id) {
    // room is seen if we are in it
    if (current_room == room_id) {
        return;
    }
    DOM_API.getRoomLinkDiv(room_id).addClass("room-not-seen");
}

export async function onUpdateVote(vote, message_id, is_add) {
    // toggle button's state
    $(this).toggleClass('active');

    if (is_add) {
        WS_API.addVote(vote, message_id);
    } else {
        WS_API.removeVote(vote, message_id);
    }
}

export async function onToggleNotifications(room_id, is_enabled) {
    WS_API.toggleNotifications(room_id, is_enabled);
}

export async function onMessageHistory(message_id) {
    let data = await WS_API.getMessageHistory(message_id);
    let history = data?.message_history || []
    
    // Format timestamps to readable dates with time
    history = history.map(entry => ({
        ...entry,
        formattedTime: formatDateTime(entry.timestamp)
    }));
    
    let html = MessageHistory( {history} );
    $("#message-history-modal .modal-body").html(html);
    $("#message-history-modal").modal('show');
}

export async function copyRoomLink(room_id, button) {
    if (!room_id) {
        return;
    }
    let link = buildRoomUrl(room_id);
    let success = await writeToClipboard(link);
    showCopyFeedback(button, success);
}

export async function copyMessageLink(room_id, message_id, button) {
    if (!room_id || !message_id) {
        return;
    }
    let link = buildMessageUrl(room_id, message_id);
    let success = await writeToClipboard(link);
    showCopyFeedback(button, success);
}

async function writeToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.warn('Clipboard API copy failed', err);
        }
    }

    let textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    let success = false;
    try {
        success = document.execCommand('copy');
    } catch (err) {
        console.warn('document.execCommand copy failed', err);
    } finally {
        document.body.removeChild(textarea);
    }

    return success;
}

function showCopyFeedback(button, success) {
    if (!button || !DOM_API || typeof DOM_API.showCopyFeedback !== 'function') {
        return;
    }
    let message = success ? _("Link copied") : _("Could not copy link");
    DOM_API.showCopyFeedback(button, message, success);
}

function buildRoomUrl(room_id) {
    return `${window.location.origin}/chat#room_id=${room_id}`;
}

function buildMessageUrl(room_id, message_id) {
    return `${buildRoomUrl(room_id)}&message_id=${message_id}`;
}

export async function onSubmitMessage(message, editing_message_id) {
    // message being edited
    if (editing_message_id) {
        let files = DOM_API.getFiles();
        let attachments = {};
        let removed_attachments = DOM_API.getRemovedAttachments();
        let original_message = DOM_API.getOriginalMessageText(editing_message_id);

        // Upload new files if any
        if (files.length) {
            let response = await WS_API.uploadFiles(files);
            attachments.images = response.filenames;
        }

        WS_API.editMessage(editing_message_id, message, attachments, removed_attachments, original_message);
        DOM_API.stopEditing();
        return;
    }


    let files = DOM_API.getFiles();
    let attachments = {};
    let is_anonymous = DOM_API.getAnonymousValue();

    if (message.replace(" ", "").length == 0 && files.length == 0) {
        return;
    }

    if (files.length) {
        let response = await WS_API.uploadFiles(files);
        attachments.images = response.filenames;
    }

    WS_API.sendMessage(current_room, message, is_anonymous, attachments);

    // remove files from input and image preview
    DOM_API.clearFiles();

    // Clears input field
    DOM_API.getMessageInput().val("");
}
