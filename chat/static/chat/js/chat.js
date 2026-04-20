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
 * Message ID being replied to (ZMIANA 2)
 * @type {number|null}
 */
let currentReplyId = null;

/**
 * Message ID to scroll to when joining a room (e.g., from link)
 * @type {number|null}
 */
let ScrollToMessageId = null;

/**
 * Current sort/filter state for messages in the active room.
 * Always reset to defaults on room change — not persisted.
 */
let SortState = { sort_by: 'date', order: 'desc', popular_only: false };

function resetSortState() {
    SortState = { sort_by: 'date', order: 'desc', popular_only: false };
}

function bindSortToolbar() {
    const dateBtn = $('#chat-sort-date');
    const likesBtn = $('#chat-sort-likes');
    const popularBtn = $('#chat-filter-popular');
    if (!dateBtn || !likesBtn || !popularBtn) return;

    const applyActiveStyles = () => {
        dateBtn.classList.toggle('active', SortState.sort_by === 'date');
        likesBtn.classList.toggle('active', SortState.sort_by === 'likes');
        popularBtn.classList.toggle('active', SortState.popular_only);

        const setArrow = (btn, active) => {
            const arrow = btn.querySelector('.sort-arrow');
            if (!arrow) return;
            if (!active) { arrow.className = 'fas fa-arrow-down sort-arrow'; arrow.style.visibility = 'hidden'; return; }
            arrow.style.visibility = '';
            arrow.className = 'fas fa-arrow-' + (SortState.order === 'asc' ? 'up' : 'down') + ' sort-arrow';
        };
        setArrow(dateBtn, SortState.sort_by === 'date');
        setArrow(likesBtn, SortState.sort_by === 'likes');
    };

    const refetch = () => {
        if (CurrentRoomId == null) return;
        WS_API.fetchMessages(CurrentRoomId, SortState.sort_by, SortState.order, SortState.popular_only);
    };

    const toggleSort = (key) => {
        if (SortState.sort_by === key) {
            SortState.order = SortState.order === 'desc' ? 'asc' : 'desc';
        } else {
            SortState.sort_by = key;
            SortState.order = 'desc';
        }
        applyActiveStyles();
        refetch();
    };

    dateBtn.addEventListener('click', () => toggleSort('date'));
    likesBtn.addEventListener('click', () => toggleSort('likes'));
    popularBtn.addEventListener('click', () => {
        SortState.popular_only = !SortState.popular_only;
        applyActiveStyles();
        refetch();
    });

    applyActiveStyles();
}

document.addEventListener('DOMContentLoaded', () => {
    WS_API = new WsApi();
    DOM_API = new DomApi();

    // Set the WebSocket message handler to break circular dependency
    WS_API.socketMessageHandler = onSocketMessage;

    // Handle mobile keyboard viewport changes for back button visibility
    if (window.visualViewport) {
        const handleViewportChange = () => {
            const header = document.getElementById('folded-room-header');
            if (header && window.innerWidth <= 767) { // Only on mobile
                const offsetTop = window.visualViewport.offsetTop;
                header.style.transform = `translateY(${offsetTop}px)`;
            }
        };

        window.visualViewport.addEventListener('resize', handleViewportChange);
        window.visualViewport.addEventListener('scroll', handleViewportChange);
        handleViewportChange(); // Initial call
    }

    // Handle unread filter functionality
    const unreadFilterBtn = $('#unread-filter-btn');
    let isUnreadFilterActive = false;

    // Restore filter state from localStorage
    const savedFilterState = localStorage.getItem('chat-unread-filter');
    if (savedFilterState === 'active') {
        isUnreadFilterActive = true;
        unreadFilterBtn?.classList.add('active');
        applyUnreadFilter();
    }

    unreadFilterBtn?.addEventListener('click', () => {
        isUnreadFilterActive = !isUnreadFilterActive;
        
        if (isUnreadFilterActive) {
            unreadFilterBtn.classList.add('active');
            localStorage.setItem('chat-unread-filter', 'active');
            applyUnreadFilter();
        } else {
            unreadFilterBtn.classList.remove('active');
            localStorage.removeItem('chat-unread-filter');
            removeUnreadFilter();
        }
    });

    function applyUnreadFilter() {
        // Filter rooms - show only unread using CSS class
        const allRoomLinks = $$('.room-link[data-room-id]');
        allRoomLinks.forEach(roomLink => {
            // Add class to hide read rooms
            if (!roomLink.classList.contains('room-not-seen')) {
                roomLink.classList.add('filtered-out');
            } else {
                roomLink.classList.remove('filtered-out');
            }
        });
    }

    function removeUnreadFilter() {
        const allRoomLinks = $$('.room-link[data-room-id]');
        allRoomLinks.forEach(roomLink => {
            roomLink.classList.remove('filtered-out');
        });
    }

// Function to reapply unread filter when room seen status changes
    function updateUnreadFilter() {
        if (isUnreadFilterActive) {
            applyUnreadFilter();
        }
    }

    // Make function globally available for other modules
    window.updateUnreadFilter = updateUnreadFilter;

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
    else if (data.replace_messages) onReplaceMessages(data.messages, data.room_id);
    else if (data.messages) onReceiveMessages(data.messages);
    else if (data.unsee_room) onRoomUnsee(data.unsee_room);
    else if (data.room_seen) onRoomSeen(data.room_seen);
    else if (data.notification) onReceiveNotification(data.notification);
    else if (data.update_votes)    onReceiveVotes(data.update_votes);
    else if (data.edit_message)   onReceiveEdit(data.edit_message);
    else if (data.online_data)    onReceiveOnlineUpdates(data.online_data);
    else if (data.update_reactions) onReceiveReactions(data.update_reactions);
    else if (data.messages_read)    onReceiveReadBy(data.messages_read);
    else if (data.type === 'room-tracked') onRoomTracked(data.room_id, data.tracked);
    else console.log("Cannot handle message!");
}

export async function onReceiveNotification(notification) {
    makeNotification(notification);
}

function onRoomTracked(roomId, tracked) {
    const roomDiv = document.querySelector(`.room-link[data-room-id="${roomId}"]`);
    if (!roomDiv) return;
    const btn = roomDiv.querySelector('.track-switch');
    if (btn) {
        btn.dataset.tracked = tracked ? 'true' : 'false';
        btn.classList.toggle('active', tracked);
        const icon = btn.querySelector('i');
        if (icon) icon.className = tracked ? 'fas fa-bookmark' : 'far fa-bookmark';
    }
    if (tracked) roomDiv.classList.remove('room-auto-muted');
}

/**
 * Expands the nav-cat-content (and archive section if needed) for the given room link.
 * @param {HTMLElement} roomLink - The room link element
 */
function expandCategoryForRoom(roomLink) {
    // Expand the nav-cat-content that wraps this room
    const navCatContent = roomLink.closest('.nav-cat-content');
    if (navCatContent) {
        if (!navCatContent.classList.contains('open')) {
            navCatContent.classList.add('open');
            const catId = navCatContent.id;
            const catBtn = catId ? document.querySelector(`[data-cat-content="${catId}"]`) : null;
            if (catBtn) catBtn.setAttribute('aria-expanded', 'true');
            if (catId) localStorage.setItem(`chat-cat-${catId}`, 'expanded');
        }
    }

    // If it's inside an archive section, show it too
    const archiveSection = roomLink.closest('.archive-section');
    if (archiveSection) {
        archiveSection.classList.add('visible');
        const archiveSectionId = archiveSection.id; // e.g. 'content-pub-rooms-archive'
        const targetId = archiveSectionId.replace('content-', ''); // e.g. 'pub-rooms-archive'
        const archiveBtn = document.querySelector(`.archive-toggle[data-target="${targetId}"]`);
        if (archiveBtn) {
            archiveBtn.classList.add('active');
            localStorage.setItem(`chat-archive-${targetId}`, 'visible');
        }
    }
}

/**
 * Build breadcrumb parts array for a given room_id by walking the sidebar DOM.
 * @param {number|string} room_id
 * @returns {Array<{label: string, active?: boolean}>}
 */
function deriveBreadcrumb(room_id) {
    const link = DOM_API.getRoomLinkDiv(room_id);
    if (!link) return [];

    const parts = [];

    // L0 — category label from the nav-cat-btn
    const navCatContent = link.closest('.nav-cat-content');
    if (navCatContent) {
        const catId = navCatContent.id;
        const catBtn = catId ? document.querySelector(`[data-cat-content="${catId}"]`) : null;
        if (catBtn) {
            // Extract text nodes only (skip .nav-cat-arrow span)
            const label = Array.from(catBtn.childNodes)
                .filter(n => n.nodeType === Node.TEXT_NODE)
                .map(n => n.textContent.trim())
                .filter(Boolean)
                .join('');
            if (label) parts.push({ label });
        }
    }

    // Leaf — room name (may show override_label = task/vote title)
    const roomName = link.querySelector('.room-name')?.textContent?.trim();
    if (roomName) parts.push({ label: roomName, active: true });

    return parts;
}

export async function onRoomTryJoin(room_id) {
    if (room_id == CurrentRoomId) return; // already in this room
    if (RoomLock.locked()) await RoomLock.wait();
    if (CurrentRoomId) await onRoomTryLeave(false);

    DOM_API.getRoomLinkDiv(room_id)?.classList.add("joined");
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
    resetSortState();
    bindSortToolbar();
    DOM_API.updateBreadcrumb(deriveBreadcrumb(room_id));
    DOM_API.setFoldedRoomTitle(response.title);
    DOM_API.showFoldedRoomHeader();
    
    // Auto-expand category and archive section if needed
    const roomLink = DOM_API.getRoomLinkDiv(room_id);
    if (roomLink) {
        expandCategoryForRoom(roomLink);
    }
    
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
    resetSortState();
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
            message.attachments, message.timestamp, message.latest_timestamp,
            message.reply_to ?? null,
            message.reactions ?? { bulb: 0, question: 0 },
            message.your_reactions ?? [],
            message.read_by ?? []
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
 * Replace all rendered messages after a sort/filter fetch.
 * Clears existing messages and re-renders them in the order returned by server.
 */
export async function onReplaceMessages(messages, room_id) {
    if (room_id != CurrentRoomId) {
        console.warn("replace_messages for wrong room", room_id, CurrentRoomId);
        return;
    }

    const msgdiv = DOM_API.getMessagesDiv();
    if (!msgdiv) return;
    msgdiv.innerHTML = '';

    if (!messages || !messages.length) {
        DOM_API.removeNoMessagesBanner();
        msgdiv.insertAdjacentHTML('beforeend', `<div class='empty-chat-message'>${_("No messages match the current filter.")}</div>`);
        return;
    }

    for (const message of messages) {
        DOM_API.addMessage(
            message.room_id, message.message_id, message.username, message.message,
            message.upvotes, message.downvotes, message.your_vote, message.own, message.edited,
            message.attachments, message.timestamp, message.latest_timestamp,
            message.reply_to ?? null,
            message.reactions ?? { bulb: 0, question: 0 },
            message.your_reactions ?? [],
            message.read_by ?? []
        );
        if (message.your_vote) {
            DOM_API.getVoteDiv(message.message_id, message.your_vote)?.classList.add('active');
        }
    }

    msgdiv.scrollTop = 0;
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
        const active_btn = DOM_API.getVoteDiv(event.message_id, event.your_vote);
        if (message_div) $$('.msg-vote', message_div).forEach(btn => btn.classList.remove('active'));
        if (event.add) active_btn?.classList.add('active');
    }

    // ZMIANA 4A — update vote bar after vote change
    DOM_API.updateVoteBar(event.message_id, event.upvotes, event.downvotes);
}

/**
 * ZMIANA 4B — update emoji reaction counts + active state for a message.
 */
export async function onReceiveReactions(event) {
    const msgDiv = DOM_API.getMessageDiv(event.message_id);
    if (!msgDiv) return;

    // Update counts
    for (const [key, count] of Object.entries(event.counts || {})) {
        const countEl = $(`.reaction-btn[data-reaction="${key}"] .reaction-count`, msgDiv);
        const btn = $(`.reaction-btn[data-reaction="${key}"]`, msgDiv);
        if (!btn) continue;
        if (count > 0) {
            if (countEl) {
                countEl.textContent = count;
            } else {
                btn.insertAdjacentHTML('beforeend', `<span class="reaction-count">${count}</span>`);
            }
        } else if (countEl) {
            countEl.remove();
        }
    }

    // Toggle active state if it was the current user
    if (event.your_reaction !== undefined && event.your_reaction !== null) {
        const btn = $(`.reaction-btn[data-reaction="${event.your_reaction}"]`, msgDiv);
        if (btn) btn.classList.toggle('reaction-btn--active', event.added ?? false);
    }
}

/**
 * ZMIANA 4C — update "read by" avatars for a message.
 */
export async function onReceiveReadBy(event) {
    const msgDiv = DOM_API.getMessageDiv(event.message_id);
    if (!msgDiv) return;
    const readByDiv = $('.msg-read-by', msgDiv);
    if (!readByDiv) return;

    const readBy = event.read_by || [];
    const visible = readBy.slice(0, 3);
    const extra = readBy.length - visible.length;
    readByDiv.innerHTML = visible.map(u =>
        `<img class="msg-avatar" src="${u.avatar_url}" title="${u.username}" alt="${u.username}">`
    ).join('') + (extra > 0 ? `<span class="msg-read-extra">+${extra}</span>` : '');
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
    updateUnreadFilter();
}

export async function onRoomSeen(room_id) {
    DOM_API.getRoomLinkDiv(room_id)?.classList.remove("room-not-seen");
    DOM_API.setRoomSeenIconState(room_id, true);
    updateUnreadFilter();
}

/**
 * Set a message as the current reply target (ZMIANA 2).
 * Updates the reply-preview bar in the input area.
 */
export function setReplyTarget(message_id, username, snippet) {
    currentReplyId = message_id;
    const preview = document.getElementById('reply-preview');
    const previewText = document.getElementById('reply-preview-text');
    if (preview && previewText) {
        previewText.textContent = `${username}: ${snippet}`;
        preview.style.display = '';
    }
}

/**
 * Clear the current reply target (ZMIANA 2).
 */
export function clearReplyTarget() {
    currentReplyId = null;
    const preview = document.getElementById('reply-preview');
    if (preview) preview.style.display = 'none';
}

/**
 * ZMIANA 4B — send toggle-reaction command to server.
 */
export function onToggleReaction(reaction, message_id) {
    WS_API?.toggleReaction(reaction, message_id);
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
        const messageText = (typeof message === 'string')
            ? (message.replace(/<[^>]*>/g, '').trim())
            : '';
        if (messageText.length === 0 && (!files || files.length === 0)) return;
        if (files?.length) {
            attachments.images = (await WS_API.uploadFiles(files)).filenames;
        }
        WS_API.sendMessage(CurrentRoomId, message, DOM_API.getAnonymousValue(), attachments, currentReplyId);
        clearReplyTarget();
        // remove files from input and image preview
        DOM_API.clearFiles();
        const messageInput = DOM_API.getMessageInput();
        if (messageInput) {
            if (messageInput.isContentEditable) {
                messageInput.innerHTML = '';
            } else {
                messageInput.value = '';
                messageInput.style.height = 'auto';
                messageInput.style.height = '38px';
            }
            messageInput.dispatchEvent(new Event('input'));
        }
        // Reset editing mode if it was active
        if (DOM_API.isEditing()) {
            DOM_API.stopEditing();
        }
    }
}