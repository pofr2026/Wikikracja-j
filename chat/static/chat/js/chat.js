/**
 * @file
 * Main chat module for handling chat room interactions, message processing, and room management.
 * Coordinates between WebSocket API (WsApi) and DOM API (DomApi) to provide chat functionality.
 */

import WsApi from './wsapi.js';
import DomApi from './domapi.js';
import { makeNotification, formatDate, formatDateTime, Lock, parseParms, _, $, $$ } from './utility.js';
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

/**
 * Initialize chat module when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    WS_API = new WsApi();
    DOM_API = new DomApi();

    // Set the WebSocket message handler to break circular dependency
    WS_API.socketMessageHandler = onSocketMessage;

    WS_API.wsOnConnect = async () => {
        // Request data about who is online
        let response = await WS_API.getOnlineUsers();
        for (let user of response.online_data) {
            DOM_API.updateOnline(user.room_id, user.online);
        }

        let data = await WS_API.getNotificationData();
        const enabledRooms = new Set(data.rooms.map(id => parseInt(id)));
        const notifButtons = $$('.notif-switch[data-room-id]');
        notifButtons.forEach(function(btn) {
            const id = parseInt(btn.dataset.roomId);
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
        const roomLinks = $$('.room-link[data-room-id]');
        const allowedRoomIds = new Set();
        roomLinks.forEach(function(el) {
            allowedRoomIds.add(parseInt(el.dataset.roomId));
        });

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
            const publicRooms = $$('.room-link[data-room-id][data-room-type="public"]');
            if (publicRooms.length > 0) {
                room_id = parseInt(publicRooms[0].dataset.roomId);
            } else if (allowedRoomIds.size > 0) {
                room_id = [...allowedRoomIds][0];
            }
        }

        if (room_id)
            onRoomTryJoin(room_id);
    };
});

/**
 * Routes incoming WebSocket messages to appropriate handlers
 * @param {Object} data - WebSocket message data
 * @param {number} [data.join] - Room ID (deprecated)
 * @param {number} [data.leave] - Room ID to leave (deprecated)
 * @param {Array} [data.messages] - Array of message objects
 * @param {number} [data.unsee_room] - Room ID to mark as unread
 * @param {Object} [data.notification] - Notification data
 * @param {Object} [data.update_votes] - Vote update data
 * @param {Object} [data.edit_message] - Edit information
 * @param {Array} [data.online_data] - Online status updates
 */
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
        let notif = data.notification;
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
    const roomLink = $(`.room-link[data-room-id="${room_id}"]`);
    if (!roomLink) return;

    const container = roomLink.closest('.list-of-rooms, .list-of-pms');
    if (!container) return;

    const containerId = container.id;
    const categoryMap = {
        'content-pub-rooms-active': '#toggleButtonPubRoomsActive',
        'content-pub-rooms-archive': '#toggleButtonPubRoomsArchive',
        'content-tasks-active': '#toggleButtonTasksActive',
        'content-tasks-archive': '#toggleButtonTasksArchive',
        'content-votes-active': '#toggleButtonVotesActive',
        'content-votes-archive': '#toggleButtonVotesArchive',
        'content-prv-active': '#toggleButtonPrvActive',
        'content-prv-archive': '#toggleButtonPrvArchive'
    };

    const toggleSelector = categoryMap[containerId];
    if (toggleSelector) {
        const toggleButton = $(toggleSelector);
        if (toggleButton) {
            // Check if container is hidden
            const isHidden = container.style.display === 'none' || getComputedStyle(container).display === 'none';
            if (isHidden) {
                // Directly show container and activate button
                container.style.display = 'block';
                container.style.height = '';
                container.style.overflow = '';
                toggleButton.classList.add('activated');
            }
        }
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

    const roomLink = DOM_API.getRoomLinkDiv(room_id);
    if (roomLink) {
        roomLink.classList.add("joined");
    }

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
            const link = DOM_API.getRoomLinkDiv(room_id);
            if (link) {
                link.classList.remove("joined");
            }
            const roomElements = $$('.room-link[data-room-id][data-room-type="public"]');
            if (roomElements.length > 0) {
                let fallbackId = parseInt(roomElements[0].dataset.roomId);
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
    const msgInput = $("#message-input");
    if (msgInput) {
        msgInput.focus();
    }
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
    const roomLink = DOM_API.getRoomLinkDiv(currentRoomId);
    if (roomLink) {
        roomLink.classList.remove("joined");
    }
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
        let banners = DOM_API.getLastMessageBanner();
        let previous_banner = banners.length ? banners[banners.length - 1].textContent : null;

        if (previous_banner != current_banner) {
            msgdiv.insertAdjacentHTML('beforeend', `<div class='date-banner'>${current_banner}</div>`);
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
                });
            }
        }
        if (message.your_vote /* You voted for this message e.g. 'upvote' or 'downvote' */ ) {
            // find message div and make button appear active
            let active_btn = DOM_API.getVoteDiv(message.message_id, message.your_vote);
            if (active_btn) {
                active_btn.classList.add('active');
            }
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

    if (shouldStickToBottom && msgdiv) {
        msgdiv.scrollTop = msgdiv.scrollHeight;
    }
    const msgInput = $("#message-input");
    if (msgInput) {
        msgInput.focus();
    }
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

    const upvotesDiv = DOM_API.getMessageUpvotesCountDiv(event.message_id);
    if (upvotesDiv) {
        upvotesDiv.textContent = event.upvotes;
    }
    const downvotesDiv = DOM_API.getMessageDownvotesCountDiv(event.message_id);
    if (downvotesDiv) {
        downvotesDiv.textContent = event.downvotes;
    }

    if (event.your_vote /* vote type e.g. upvote or downvote or null if it wasn't you who triggered */ ) {
        // find vote button you pressed
        let active_btn = DOM_API.getVoteDiv(event.message_id, event.your_vote);
        // make all vote buttons appear inactive
        if (message_div) {
            const voteBtns = $$('.msg-vote', message_div);
            voteBtns.forEach(function(btn) {
                btn.classList.remove('active');
            });
        }

        // vote was added
        if (event.add) {
            if (active_btn) {
                active_btn.classList.add('active');
            }
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
    const roomLink = DOM_API.getRoomLinkDiv(room_id);
    if (roomLink) {
        roomLink.classList.add("room-not-seen");
    }
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
    this.classList.toggle('active');

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
    let history = data?.message_history || [];

    // Format timestamps to readable dates with time
    history = history.map(entry => ({
        ...entry,
        formattedTime: formatDateTime(entry.timestamp)
    }));

    let html = MessageHistory({ history });
    const modalBody = $("#message-history-modal .modal-body");
    if (modalBody) {
        modalBody.innerHTML = html;
    }
    // Bootstrap modal show
    const modal = $("#message-history-modal");
    if (modal) {
        // Use bootstrap's JS API if available, otherwise fallback to class manipulation
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
        } else {
            modal.classList.add('show');
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        }
    }
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
function buildMessageUrls(room_id, message_id) {
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
        if (files && files.length) {
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

    if (message.replace(" ", "").length == 0 && (!files || files.length == 0)) {
        return;
    }

    if (files && files.length) {
        let response = await WS_API.uploadFiles(files);
        attachments.images = response.filenames;
    }

    WS_API.sendMessage(currentRoomId, message, is_anonymous, attachments);

    // remove files from input and image preview
    DOM_API.clearFiles();

    // Clears input field
    const input = DOM_API.getMessageInput();
    if (input) {
        input.value = "";
    }
}