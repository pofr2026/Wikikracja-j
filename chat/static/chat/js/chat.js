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
let CurrentRoomId = null;

/**
 * Message ID to scroll to when joining a room (e.g., from link)
 * @type {number|null}
 */
let ScrollToMessageId = null;

document.addEventListener('DOMContentLoaded', () => {
    WS_API = new WsApi();
    DOM_API = new DomApi();

    // Set the WebSocket message handler to break circular dependency
    WS_API.socketMessageHandler = onSocketMessage;

    WS_API.wsOnConnect = async () => {
        for (const user of (await WS_API.getOnlineUsers()).online_data) {
            DOM_API.updateOnline(user.room_id, user.online);
        }

        const data = await WS_API.getNotificationData();
        const enabledRooms = new Set(data.rooms.map(id => parseInt(id)));
        $$('.notif-switch[data-room-id]').forEach(btn => {
            DOM_API.setRoomNotifications(parseInt(btn.dataset.roomId), enabledRooms.has(parseInt(btn.dataset.roomId)));
        });

        let room_id = 0;
        if (window.location.hash) {
            const obj = parseParms(window.location.hash.slice(1));
            if (obj.room_id) room_id = obj.room_id;
            if (obj.message_id) ScrollToMessageId = obj.message_id;
        }

        // Build set of room IDs the user actually has access to (rendered in DOM by server)
        const roomLinks = $$('.room-link[data-room-id]');
        const allowedRoomIds = new Set([...roomLinks].map(el => parseInt(el.dataset.roomId)));

        // Get locally stored last room ID, but only if it's in the allowed list
        if (!room_id && localStorage.lastUsedRoomID) {
            const storedId = parseInt(localStorage.lastUsedRoomID);
            if (allowedRoomIds.has(storedId)) room_id = storedId;
            else delete localStorage.lastUsedRoomID;
        }

        // Find the first public room if no room_id is set
        if (!room_id) {
            const publicRooms = $$('.room-link[data-room-id][data-room-type="public"]');
            room_id = publicRooms.length > 0 ? parseInt(publicRooms[0].dataset.roomId) : [...allowedRoomIds][0] ?? 0;
        }

        if (room_id) onRoomTryJoin(room_id);
    };
});

export async function onSocketMessage(data) {
    if (data.join || data.leave) console.warn("deprecated");
    else if (data.messages) onReceiveMessages(data.messages);
    else if (data.unsee_room) onRoomUnsee(data.unsee_room);
    else if (data.room_seen) onRoomSeen(data.room_seen);
    else if (data.notification) onReceiveNotification(data.notification);
    else if (data.update_votes) onReceiveVotes(data.update_votes);
    else if (data.edit_message) onReceiveEdit(data.edit_message);
    else if (data.online_data) onReceiveOnlineUpdates(data.online_data);
    else console.log("Cannot handle message!");
}

export async function onReceiveNotification(notification) {
    makeNotification(notification);
}

async function expandCategoryForRoom(room_id) {
    const roomLink = $(`.room-link[data-room-id="${room_id}"]`);
    if (!roomLink) return;
    const container = roomLink.closest('.list-of-rooms, .list-of-pms');
    if (!container) return;

    const categoryMap = {
        'content-pub-rooms-active': '#toggleButtonPubRoomsActive',
        'content-pub-rooms-archive': '.archive-toggle[data-target="pub-rooms-archive"]',
        'content-tasks-active': '#toggleButtonTasksActive',
        'content-tasks-archive': '.archive-toggle[data-target="tasks-archive"]',
        'content-votes-active': '#toggleButtonVotesActive',
        'content-votes-archive': '.archive-toggle[data-target="votes-archive"]',
        'content-prv-active': '#toggleButtonPrvActive',
        'content-prv-archive': '.archive-toggle[data-target="prv-archive"]'
    };

    const toggleButton = $(categoryMap[container.id]);
    if (toggleButton) {
        // Only expand if the user hasn't manually collapsed it
        // Check if the accordion button is not activated (meaning it's collapsed)
        if (toggleButton.classList.contains('accordion') && !toggleButton.classList.contains('activated')) {
            // User manually collapsed this category, don't auto-expand
            return;
        }
        
        const isHidden = container.style.display === 'none' || getComputedStyle(container).display === 'none';
        if (isHidden) {
            container.style.display = 'block';
            container.style.height = '';
            container.style.overflow = '';
            if (toggleButton.classList.contains('accordion')) {
                toggleButton.classList.add('activated');
            } else {
                toggleButton.classList.add('active');
            }
        }
    }
}

export async function onRoomTryJoin(room_id) {
    if (room_id == CurrentRoomId) return; // already in this room
    if (RoomLock.locked()) await RoomLock.wait();
    if (CurrentRoomId) await onRoomTryLeave(false);

    DOM_API.getRoomLinkDiv(room_id)?.classList.add("joined");
    expandCategoryForRoom(room_id); // Expand category containing this room
    if (CurrentRoomId) return; // joined another room while awaiting confirmation

    RoomLock.lock();
    let response;
    try {
        response = await WS_API.joinRoom(room_id);
    } catch (error) {
        RoomLock.unlock();
        if (error === 'ROOM_INVALID' || error === 'ACCESS_DENIED') {
            delete localStorage.lastUsedRoomID;
            DOM_API.getRoomLinkDiv(room_id)?.classList.remove("joined");
            const roomLinks = $$('.room-link[data-room-id][data-room-type="public"]')[0];
            if (roomLinks && parseInt(roomLinks.dataset.roomId) != room_id) {
                onRoomTryJoin(parseInt(roomLinks.dataset.roomId));
            }
        } else alert(error);
        return;
    }
    RoomLock.unlock();

    localStorage.lastUsedRoomID = room_id;
    CurrentRoomId = room_id;
    // TODO: send seen confirmation to server after a little while
    DOM_API.seenChat(room_id);
    WS_API.seenRoom(room_id);
    DOM_API.setRoomNotifications(response.notifications);
    DOM_API.createRoomDiv(CurrentRoomId, response.title, response.public, response.notifications);
    DOM_API.setFoldedRoomTitle(response.title);
    DOM_API.showFoldedRoomHeader();
    
    // Focus the message input field after joining a room
    const messageInput = DOM_API.getMessageInput();
    if (messageInput) {
        messageInput.focus();
    }
}

/**
 * @param {boolean} sync_with_server - If true, sends leave command to server
 */
export async function onRoomTryLeave(sync_with_server) {
    if (RoomLock.locked()) await RoomLock.wait();
    if (sync_with_server) {
        RoomLock.lock();
        await WS_API.leaveRoom(CurrentRoomId);
        RoomLock.unlock();
    }
    DOM_API.getRoomLinkDiv(CurrentRoomId)?.classList.remove("joined");
    DOM_API.clearRoomData();
    DOM_API.hideFoldedRoomHeader();
    CurrentRoomId = null;
}

/**
 * Handle back button click - leave room and show room list on mobile
 */
export async function onBackToRoomList() {
    if (CurrentRoomId) {
        await onRoomTryLeave(false);
    }
}

/**
 * @param {Array} messages - Array of message objects from server
 */
export async function onReceiveMessages(messages) {
    const room_id = messages[0].room_id;
    if (room_id != CurrentRoomId) {
        console.warn("received message for wrong room");
        return;
    }

    const msgdiv = DOM_API.getMessagesDiv();
    DOM_API.removeNoMessagesBanner();

    for (const message of messages) {
        const current_banner = formatDate(message.timestamp);
        const banners = DOM_API.getLastMessageBanner();
        const previous_banner = banners.length ? banners[banners.length - 1].textContent : null;
        if (previous_banner != current_banner) {
            msgdiv.insertAdjacentHTML('beforeend', `<div class='date-banner'>${current_banner}</div>`);
        }

        DOM_API.addMessage(
            message.room_id, message.message_id, message.username, message.message,
            message.upvotes, message.downvotes, message.your_vote, message.own, message.edited,
            message.attachments, message.timestamp, message.latest_timestamp
        );

        if (message.new && document.hidden && !message.own) {
            makeNotification({ title: message.username, body: message.message });
        }
        if (message.your_vote/* You voted for this message e.g. 'upvote' or 'downvote' */) {
            // find message div and make button appear active
            DOM_API.getVoteDiv(message.message_id, message.your_vote)?.classList.add('active');
        }
    }

    let shouldStickToBottom = !ScrollToMessageId;
    if (ScrollToMessageId) {
        const didScroll = DOM_API.scrollToMessage(ScrollToMessageId);
        if (didScroll) {
            shouldStickToBottom = false;
            ScrollToMessageId = null;
        }
    }
    if (shouldStickToBottom && msgdiv) msgdiv.scrollTop = msgdiv.scrollHeight;
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
    const message_div = DOM_API.getMessageDiv(event.message_id);
    DOM_API.getMessageUpvotesCountDiv(event.message_id).textContent = event.upvotes;
    DOM_API.getMessageDownvotesCountDiv(event.message_id).textContent = event.downvotes;

    if (event.your_vote /* vote type e.g. upvote or downvote or null if it wasn't you who triggered */) {
        // find vote button you pressed
        const active_btn = DOM_API.getVoteDiv(event.message_id, event.your_vote);
        // make all vote buttons appear inactive
        if (message_div) $$('.msg-vote', message_div).forEach(btn => btn.classList.remove('active'));
        // vote was added
        if (event.add) active_btn?.classList.add('active');
    }
}

export async function onReceiveEdit(edit_info) {
    DOM_API.editMessageText(edit_info.message_id, edit_info.text, edit_info.timestamp);
    if (edit_info.attachments !== undefined) {
        DOM_API.updateMessageAttachments(edit_info.message_id, edit_info.attachments);
    }
    DOM_API.showHistoryButton(edit_info.message_id);
    
    // Stop editing mode if this was the message being edited
    const editedId = DOM_API.getEditedMessageId();
    
    // Convert both to strings for comparison since message_id can be string or number
    const editedIdStr = editedId ? String(editedId) : null;
    const messageIdStr = String(edit_info.message_id);
    
    if (DOM_API.isEditing() && editedIdStr && editedIdStr === messageIdStr) {
        DOM_API.stopEditing();
    }
}

export async function onReceiveOnlineUpdates(updates) {
    for (const update of updates) {
        DOM_API.updateOnline(update.room_id, update.online);
    }
}

export async function onRoomUnsee(room_id) {
    if (CurrentRoomId == room_id) return;
    DOM_API.getRoomLinkDiv(room_id)?.classList.add("room-not-seen");
    DOM_API.setRoomSeenIconState(room_id, false);
}

export async function onRoomSeen(room_id) {
    DOM_API.getRoomLinkDiv(room_id)?.classList.remove("room-not-seen");
    DOM_API.setRoomSeenIconState(room_id, true);
}

export async function onUpdateVote(vote, message_id, is_add) {
    this.classList.toggle('active');
    is_add ? WS_API.addVote(vote, message_id) : WS_API.removeVote(vote, message_id);
}

export async function onToggleNotifications(room_id, is_enabled) {
    WS_API.toggleNotifications(room_id, is_enabled);
}

export async function onToggleSeen(room_id, is_seen) {
    if (is_seen) {
        WS_API.seenRoom(room_id);
    } else {
        WS_API.markRoomUnseen(room_id);
    }
}

export async function onMessageHistory(message_id) {
    const data = await WS_API.getMessageHistory(message_id);
    const history = (data?.message_history || []).map(entry => ({
        ...entry, formattedTime: formatDateTime(entry.timestamp)
    }));

    $("#message-history-modal .modal-body").innerHTML = MessageHistory({ history });
    const modal = $("#message-history-modal"); // Bootstrap modal show
    if (modal) {
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            new bootstrap.Modal(modal).show();
        } else {
            modal.classList.add('show');
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        }
    }
}

export async function copyRoomLink(room_id, button) {
    if (!room_id) return;
    const success = await writeToClipboard(buildRoomUrl(room_id));
    showCopyFeedback(button, success);
}

export async function copyMessageLink(room_id, message_id, button) {
    if (!room_id || !message_id) return;
    const success = await writeToClipboard(buildMessageUrl(room_id, message_id));
    showCopyFeedback(button, success);
}

async function writeToClipboard(text) {
    if (navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) { console.warn('Clipboard API copy failed', err); }
    }
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    let success = false;
    try { success = document.execCommand('copy'); }
    catch (err) { console.warn('document.execCommand copy failed', err); }
    finally { document.body.removeChild(textarea); }
    return success;
}

function showCopyFeedback(button, success) {
    if (!button || !DOM_API || typeof DOM_API.showCopyFeedback !== 'function') return;
    DOM_API.showCopyFeedback(button, success ? _("Link copied") : _("Could not copy link"), success);
}

function buildRoomUrl(room_id) {
    return `${window.location.origin}/chat#room_id=${room_id}`;
}

function buildMessageUrl(room_id, message_id) {
    return `${buildRoomUrl(room_id)}&message_id=${message_id}`;
}

export async function onSubmitMessage(message, editing_message_id) {
    if (editing_message_id) {
        const files = DOM_API.getFiles();
        const attachments = {};
        // Upload new files if any
        if (files?.length) {
            attachments.images = (await WS_API.uploadFiles(files)).filenames;
        }
        WS_API.editMessage(editing_message_id, message, attachments, DOM_API.getRemovedAttachments(), DOM_API.getOriginalMessageText(editing_message_id));
        // Don't stop editing immediately - let onReceiveEdit handle it after server confirms
    } else {
        const files = DOM_API.getFiles();
        const attachments = {};
        if (message.replace(" ", "").length == 0 && (!files || files.length == 0)) return;
        if (files?.length) {
            attachments.images = (await WS_API.uploadFiles(files)).filenames;
        }
        WS_API.sendMessage(CurrentRoomId, message, DOM_API.getAnonymousValue(), attachments);
        // remove files from input and image preview
        DOM_API.clearFiles();
        const messageInput = DOM_API.getMessageInput();
        messageInput.value = "";
        messageInput.style.height = 'auto';
        messageInput.style.height = '38px';
        // Reset editing mode if it was active
        if (DOM_API.isEditing()) {
            DOM_API.stopEditing();
        }
    }
}