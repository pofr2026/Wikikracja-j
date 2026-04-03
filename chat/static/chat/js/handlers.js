/**
 * @file
 * Event handlers module for chat UI interactions.
 * Sets up DOM event listeners and routes events to appropriate handler functions.
 */

import {
    onSubmitMessage,
    onUpdateVote,
    onRoomTryJoin,
    onToggleNotifications,
    onMessageHistory,
    copyRoomLink,
    copyMessageLink,
} from './chat.js';

import DomApi from './domapi.js';
import { $, $$ } from './utility.js';

/**
 * DOM API instance for UI operations
 * @type {DomApi}
 */
const DOM_API = new DomApi();

document.addEventListener('DOMContentLoaded', () => {
    const accordionMap = {
        'toggleButtonPubRoomsActive': 'content-pub-rooms-active',
        'toggleButtonPubRoomsArchive': 'content-pub-rooms-archive',
        'toggleButtonTasksActive': 'content-tasks-active',
        'toggleButtonTasksArchive': 'content-tasks-archive',
        'toggleButtonVotesActive': 'content-votes-active',
        'toggleButtonVotesArchive': 'content-votes-archive',
        'toggleButtonPrvActive': 'content-prv-active',
        'toggleButtonPrvArchive': 'content-prv-archive'
    };

    for (const acc of document.getElementsByClassName('accordion')) {
        acc.addEventListener('click', () => {
            this.classList.toggle('activated');
            const contentEl = $('#' + accordionMap[this.id]);
            if (contentEl) slideToggle(contentEl, 300);
        });
    }

    document.addEventListener("click", (e) => {
        if (e.target.closest(".send-message")) {
            onSubmitMessage(DOM_API.getEnteredText(), DOM_API.getEditedMessageId());
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.target.id !== "message-input") return;
        if (e.keyCode == 13) {
            onSubmitMessage(DOM_API.getEnteredText(), DOM_API.getEditedMessageId());
        }
        if (e.key == "ArrowUp") {
            e.preventDefault();
            const message = DOM_API.getLatestOwnMessage();
            if (!DOM_API.isEditing()) {
                DOM_API.setEditing(message?.dataset.messageId);
            }
        }
    });

    document.addEventListener('click', (e) => {
        const container = e.target.closest('.attachment-image-container');
        if (container) {
            DOM_API.openBigImage([...$$("img", container)].map(img => img.src));
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.notif-switch');
        if (btn) {
            const newState = !(btn.dataset.enabled === "true" || btn.dataset.enabled === true);
            btn.dataset.enabled = newState;
            const icon = $("i", btn);
            icon?.classList.toggle('fa-bell', newState);
            icon?.classList.toggle('fa-bell-slash', !newState);
            onToggleNotifications(btn.dataset.roomId, newState);
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === "Escape" && DOM_API.isEditing()) {
            DOM_API.stopEditing();
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.delete-images-preview');
        if (btn) DOM_API.clearFiles(btn.dataset.roomId);
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.copy-room-url');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            copyRoomLink(btn.dataset.roomId, btn);
        }
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.copy-message-url');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            copyMessageLink(btn.dataset.roomId, btn.dataset.messageId, btn);
        }
    });

    document.addEventListener("change", (e) => {
        if (!e.target.classList.contains("file-input")) return;
        const files = e.target.files;
        const preview_container = DOM_API.getPreviewDiv();
        if (!DOM_API.isEditing() && preview_container) preview_container.innerHTML = '';
        if (files.length > 0) DOM_API.getPreviewContainer().style.display = '';
        for (let i = 0; i < files.length; ++i) {
            const file = files.item(i);
            const fr = new FileReader();
            const preview_id = `preview-new-${i}-${Date.now()}`;
            preview_container?.insertAdjacentHTML('beforeend', `<div class="image-preview-wrapper" style="position: relative; display: inline-block;">
                <img class='image-preview new-attachment' id='${preview_id}'>
                <button class="btn btn-sm btn-danger remove-new-attachment"
                    style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 12px;"
                    data-preview-id="${preview_id}" type="button">×</button>
            </div>`);
            fr.onload = (e) => {
                document.getElementById(preview_id).src = e.target.result;
            };
            fr.readAsDataURL(file);
        }
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".msg-vote");
        if (btn) {
            onUpdateVote.call(btn, btn.dataset.eventName, btn.dataset.messageId, !btn.classList.contains('active'));
        }
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".show-history");
        if (btn) onMessageHistory(btn.dataset.messageId);
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".edit-message");
        if (btn) DOM_API.setEditing(btn.dataset.messageId);
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".remove-existing-attachment");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            DOM_API.addRemovedAttachment(btn.dataset.filename);
            btn.closest('.image-preview-wrapper')?.remove();
            if (DOM_API.getPreviewDiv()?.children.length === 0) {
                DOM_API.getPreviewContainer().style.display = 'none';
            }
        }
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".remove-new-attachment");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            btn.closest('.image-preview-wrapper')?.remove();
            const previewDiv = DOM_API.getPreviewDiv();
            if (previewDiv && $$('.new-attachment', previewDiv).length === 0) {
                DOM_API.getFileInput().value = "";
            }
            if (previewDiv?.children.length === 0) {
                DOM_API.getPreviewContainer().style.display = 'none';
            }
        }
    });

    document.addEventListener('click', handleRoomNameClick);
    document.addEventListener('touchstart', handleRoomNameClick, { passive: false });

    function handleRoomNameClick(e) {
        const roomName = e.target.closest('.room-name');
        if (!roomName) return;
        if (e.type === 'touchstart') e.preventDefault();
        const room_id = roomName.parentElement.getAttribute("data-room-id");
        if (!roomName.classList.contains("joined")) {
            roomName.parentElement.classList.add('room-tapping');
            setTimeout(() => roomName.parentElement.classList.remove('room-tapping'), 300);
            onRoomTryJoin(room_id);
        }
    }
});

function slideToggle(element, duration) {
    const isHidden = element.style.display === 'none' || getComputedStyle(element).display === 'none';
    element.style.overflow = 'hidden';
    if (isHidden) {
        element.style.display = 'block';
        element.style.height = '0';
        animate(element, { height: element.scrollHeight + 'px' }, duration);
    } else {
        element.style.height = element.scrollHeight + 'px';
        animate(element, { height: '0' }, duration, () => {
            element.style.display = 'none';
            element.style.height = '';
            element.style.overflow = '';
        });
    }
}

function animate(element, properties, duration, callback) {
    element.style.transition = `height ${duration}ms ease`;
    for (const prop in properties) {
        element.style[prop] = properties[prop];
    }
    const onTransitionEnd = () => {
        element.removeEventListener('transitionend', onTransitionEnd);
        callback?.();
    };
    element.addEventListener('transitionend', onTransitionEnd);
}