/**
 * @file
 * Main chat module for handling chat room interactions, message processing, and room management.
 * Coordinates between WebSocket API (WsApi) and DOM API (DomApi) to provide chat functionality.
 */

import WsApi from './wsapi.js';
import DomApi from './domapi.js';
import { makeNotification, formatDate, formatDateTime, Lock, parseParms, _ } from './utility.js';
import { MessageHistory } from './templates.js';

/**
 * Global WebSocket API instance
 * @type {WsApi}
 */
let WS_API;

/**
 * Global DOM API instance
 * @type {DomApi}
 */
let DOM_API;

/**
 * Lock for preventing concurrent room join/leave operations
 * @type {Lock}
 */
const RoomLock = new Lock();

/**
 * Currently active room ID
 * @type {number|null}
 */
let currentRoomId = null;

/**
 * Message ID to scroll to when joining a room (e.g., from link)
 * @type {number|null}
 */
let scrollToMessageId = null;

$(() => {
    WS_API = new WsApi();
    DOM_API = new DomApi();
    
    WS_API.wsOnConnect = async() => {
        // Request data about who is online
        let response = await WS_API.getOnlineUsers();
        for (let user of response.online_data) {
            DOM_API.updateOnline(user.room_id, user.online);
        }

        let data = await WS_API.getNotificationData();
        const enabledRooms = new Set(data.rooms.map(id => parseInt(id)));
        $('.notif-switch[data-room-id]').each(function() {
            const id = parseInt($(this).data('room-id'));
            DOM_API.setRoomNotifications(id, enabledRooms.has(id));
        });

        let room_id = 0;
        if (window.location.hash) {
            // Get room ID passed with url hash
            let hash = window.location.hash.slice(1);
            let obj = parseParms(hash);
            if (obj.room_id) {
                room_id = obj.room_id;
            }
            if (obj.message_id) {
                scrollToMessageId = obj.message_id;
            }
        }

        // Build set of room IDs the user actually has access to (rendered in DOM by server)
        const allowedRoomIds = new Set(
            $('.room-link[data-room-id]').map((_, el) => parseInt($(el).data('room-id'))).get()
        );

        // Get locally stored last room ID, but only if it's in the allowed list
        if (!room_id && localStorage.lastUsedRoomID) {
            let storedId = parseInt(localStorage.lastUsedRoomID);
            if (allowedRoomIds.has(storedId)) {
                room_id = storedId;
            } else {
                delete localStorage.lastUsedRoomID;
            }
        }

        // Find the first public room if no room_id is set
        if (!room_id) {
            let publicRooms = $('.room-link[data-room-id][data-room-type="public"]');
            if (publicRooms.length > 0) {
                room_id = parseInt($(publicRooms[0]).data('room-id'));
            } else if (allowedRoomIds.size > 0) {
                room_id = [...allowedRoomIds][0];
            }
        }

        if (room_id) 
            onRoomTryJoin(room_id);        
    }
});

/**
 * Handles incoming chat notifications
 * @param {Object} notification - Notification object
 * @param {string} notification.title - Notification title
 * @param {string} notification.body - Notification body text
 * @param {string} notif.link - Notification icon image link
 * @param {number} [notification.room_id] - Optional room ID
 */
export async function onReceiveNotification(notification) {
    makeNotification(notification);
}

    // Function to expand category containing the active room
async function expandCategoryForRoom(room_id) {
      const roomLink = $(`.room-link[data-room-id="${room_id}"]`)
      if (roomLink.length === 0) return
      
      const container = roomLink.closest('.list-of-rooms, .list-of-pms')
      if (container.length === 0) return
      
      const containerId = container.attr('id')
      const categoryMap = {
        'content-pub-rooms-active': '#toggleButtonPubRoomsActive',
        'content-pub-rooms-archive': '#toggleButtonPubRoomsArchive',
        'content-tasks-active': '#toggleButtonTasksActive',
        'content-tasks-archive': '#toggleButtonTasksArchive',
        'content-votes-active': '#toggleButtonVotesActive',
        'content-votes-archive': '#toggleButtonVotesArchive',
        'content-prv-active': '#toggleButtonPrvActive',
        'content-prv-archive': '#toggleButtonPrvArchive'
      }
      
      const toggleButton = categoryMap[containerId]
      if (toggleButton && !$(toggleButton).hasClass('activated')) {
        container.show()
        $(toggleButton).addClass('activated')
      }
    }

export async function onRoomTryJoin(room_id) {
    // already in this room
    if (room_id == currentRoomId) {
        return;
    }

    if (RoomLock.locked()) {
        await RoomLock.wait();
    }

    if (currentRoomId) {
        // only do client stuff, user will leave
        // serverside automatically with join
        await onRoomTryLeave(false);
    }

    DOM_API.getRoomLinkDiv(room_id).addClass("joined");
    
    // Expand category containing this room
    expandCategoryForRoom(room_id);
    
    // joined another room while awaiting confirmation
    if (currentRoomId) {
        return;
    }

    RoomLock.lock();
    let response;
    try {
        response = await WS_API.joinRoom(room_id);
        const ii = 1;
        const ii2 = 1;
        
    } catch (error) {
        RoomLock.unlock();
        if (error === 'ROOM_INVALID' || error === 'ACCESS_DENIED') {
            delete localStorage.lastUsedRoomID;
            DOM_API.getRoomLinkDiv(room_id).removeClass("joined");
            let roomElements = $('.room-link[data-room-id][data-room-type="public"]');
            if (roomElements.length > 0) {
                let fallbackId = parseInt($(roomElements[0]).data('room-id'));
                if (fallbackId != room_id) {
                    onRoomTryJoin(fallbackId);
                }
            }
        } else {
            alert(error);
        }
        return;
    }
    RoomLock.unlock();

    localStorage.lastUsedRoomID = room_id;

    currentRoomId = room_id;
    let title = response.title;
    let has_notifs = response.notifications;
    let is_public = response.public;

    // TODO: send seen confirmation to server after a little while
    DOM_API.seenChat(room_id);
    WS_API.seenRoom(room_id);

    //DOM_API.setRoomTitle(title);
    DOM_API.setRoomNotifications(has_notifs);

    DOM_API.createRoomDiv(currentRoomId, title, is_public, has_notifs);

    // Put cursor into input field
    document.querySelector("#message-input").focus();
}

/**
 * Leaves the current chat room
 * @param {boolean} sync_with_server - If true, sends leave command to server
 */
export async function onRoomTryLeave(sync_with_server) {
    if (RoomLock.locked()) {
        await RoomLock.wait();
    }

    if (sync_with_server) {
        RoomLock.lock();
        await WS_API.leaveRoom(currentRoomId);
        RoomLock.unlock();
    }
    DOM_API.getRoomLinkDiv(currentRoomId).removeClass("joined");
    DOM_API.clearRoomData();

    currentRoomId = null;
}

/**
 * Processes an array of incoming messages
 * @param {Array} messages - Array of message objects from server
 * @param {number} messages[0].room_id - Room ID the messages belong to
 * @param {number} messages[0].message_id - Unique message ID
 * @param {string} messages[0].username - Sender's username
 * @param {string} messages[0].message - Message content
 * @param {number} messages[0].upvotes - Upvote count
 * @param {number} messages[0].downvotes - Downvote count
 * @param {string|null} messages[0].your_vote - Current user's vote ('upvote', 'downvote', or null)
 * @param {boolean} messages[0].own - Whether message was sent by current user
 * @param {boolean} messages[0].edited - Whether message has been edited
 * @param {Object} [messages[0].attachments] - Attachment data (images array)
 * @param {number} messages[0].timestamp - Original message timestamp
 * @param {number} messages[0].latest_timestamp - Latest message timestamp (for edited)
 * @param {boolean} messages[0].new - Whether this is a newly arrived message
 */
export async function onReceiveMessages(messages) {
    let room_id = messages[0].room_id;

    // received data for wrong room if message was delayed
    if (room_id != currentRoomId) {
        console.warn("received message for wrong room");
        return;
    }

    let msgdiv = DOM_API.getMessagesDiv();
    DOM_API.removeNoMessagesBanner();

    for (let message of messages) {
        // let type = DOM_API.getRoomType(message.room_id);
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

    let shouldStickToBottom = !scrollToMessageId;
    if (scrollToMessageId) {
        let didScroll = DOM_API.scrollToMessage(scrollToMessageId);
        if (didScroll) {
            shouldStickToBottom = false;
        }
        if (didScroll) {
            scrollToMessageId = null;
        }
    }

    if (shouldStickToBottom) {
        msgdiv.scrollTop(msgdiv.prop("scrollHeight"));
    }
    document.querySelector("#message-input").focus();
}

/**
 * Handles vote updates for a message
 * @param {Object} event - Vote update event data
 * @param {number} event.message_id - ID of the message that was voted on
 * @param {number} event.upvotes - Updated upvote count
 * @param {number} event.downvotes - Updated downvote count
 * @param {string|null} event.your_vote - Current user's vote ('upvote', 'downvote', or null)
 * @param {boolean} event.add - Whether vote was added (true) or removed (false)
 */
export async function onReceiveVotes(event) {
    // find message on page by id and update counters
    let message_div = DOM_API.getMessageDiv(event.message_id);

    DOM_API.getMessageUpvotesCountDiv(event.message_id).text(event.upvotes);
    DOM_API.getMessageDownvotesCountDiv(event.message_id).text(event.downvotes);

    if (event.your_vote /* vote type e.g. upvote or downvote or null if it wasn't you who triggered */ ) {
        // find vote button you pressed
        let active_btn = DOM_API.getVoteDiv(event.message_id, event.your_vote);
        // make all vote buttons appear inactive
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

/**
 * Handles message edit events
 * @param {Object} edit_info - Edit information from server
 * @param {number} edit_info.message_id - ID of the edited message
 * @param {string} edit_info.text - New message text
 * @param {number} edit_info.timestamp - Edit timestamp
 * @param {Object} [edit_info.attachments] - Updated attachments (optional)
 */
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

/**
 * Updates online status for multiple rooms
 * @param {Array} updates - Array of online status updates
 * @param {number} updates[].room_id - Room ID
 * @param {boolean} updates[].online - Whether room is online
 */
export async function onReceiveOnlineUpdates(updates) {
    for (let update of updates) {
        DOM_API.updateOnline(update.room_id, update.online);
    }
};

/**
 * Marks a room as unread (shows notification indicator)
 * @param {number} room_id - ID of the room to mark as unread
 */
export async function onRoomUnsee(room_id) {
    // room is seen if we are in it
    if (currentRoomId == room_id) {
        return;
    }
    DOM_API.getRoomLinkDiv(room_id).addClass("room-not-seen");
}

/**
 * Updates a vote on a message (adds or removes)
 * @param {string} vote - Vote type ('upvote' or 'downvote')
 * @param {number} message_id - ID of the message
 * @param {boolean} is_add - true to add vote, false to remove vote
 * @this {HTMLElement} - The clicked vote button element
 */
export async function onUpdateVote(vote, message_id, is_add) {
    // toggle button's state
    $(this).toggleClass('active');

    if (is_add) {
        WS_API.addVote(vote, message_id);
    } else {
        WS_API.removeVote(vote, message_id);
    }
}

/**
 * Toggles push notifications for a specific room
 * @param {number} room_id - ID of the room
 * @param {boolean} is_enabled - Whether notifications are enabled
 */
export async function onToggleNotifications(room_id, is_enabled) {
    WS_API.toggleNotifications(room_id, is_enabled);
}

/**
 * Fetches and displays message edit history
 * @param {number} message_id - ID of the message to show history for
 */
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

/**
 * Copies a room link to clipboard
 * @param {number} room_id - ID of the room
 * @param {HTMLElement} button - Button element that triggered the copy (for feedback)
 */
export async function copyRoomLink(room_id, button) {
    if (!room_id) {
        return;
    }
    let link = buildRoomUrl(room_id);
    let success = await writeToClipboard(link);
    showCopyFeedback(button, success);
}

/**
 * Copies a message link to clipboard
 * @param {number} room_id - ID of the room
 * @param {number} message_id - ID of the message
 * @param {HTMLElement} button - Button element that triggered the copy (for feedback)
 */
export async function copyMessageLink(room_id, message_id, button) {
    if (!room_id || !message_id) {
        return;
    }
    let link = buildMessageUrl(room_id, message_id);
    let success = await writeToClipboard(link);
    showCopyFeedback(button, success);
}

/**
 * Writes text to clipboard using modern or fallback API
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} - true if copy succeeded, false otherwise
 */
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

/**
 * Shows visual feedback after copy operation
 * @param {HTMLElement} button - Button element to show feedback on
 * @param {boolean} success - Whether copy succeeded
 */
function showCopyFeedback(button, success) {
    if (!button || !DOM_API || typeof DOM_API.showCopyFeedback !== 'function') {
        return;
    }
    let message = success ? _("Link copied") : _("Could not copy link");
    DOM_API.showCopyFeedback(button, message, success);
}

/**
 * Builds a room URL
 * @param {number} room_id - ID of the room
 * @returns {string} - Full URL to the room
 */
function buildRoomUrl(room_id) {
    return `${window.location.origin}/chat#room_id=${room_id}`;
}

/**
 * Builds a message URL
 * @param {number} room_id - ID of the room
 * @param {number} message_id - ID of the message
 * @returns {string} - Full URL to the specific message
 */
function buildMessageUrl(room_id, message_id) {
    return `${buildRoomUrl(room_id)}&message_id=${message_id}`;
}

/**
 * Handles message submission (new or edited)
 * @param {string} message - Message text content
 * @param {number|null} editing_message_id - If editing, the message ID being edited; null for new message
 */
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

    WS_API.sendMessage(currentRoomId, message, is_anonymous, attachments);

    // remove files from input and image preview
    DOM_API.clearFiles();

    // Clears input field
    DOM_API.getMessageInput().val("");
}