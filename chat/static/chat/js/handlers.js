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

/**
 * Sets up event listeners for the chat interface
 */
document.addEventListener('DOMContentLoaded', function() {

    // Map accordion button IDs to their content element IDs
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

    let acc = document.getElementsByClassName('accordion');
    for (var i = 0; i < acc.length; i++) {
        acc[i].addEventListener('click', function() {
            this.classList.toggle('activated');
            // Find the associated content element and slide toggle it
            const contentId = accordionMap[this.id];
            if (contentId) {
                const contentEl = $('#' + contentId);
                if (contentEl) {
                    slideToggle(contentEl, 300);
                }
            }
        });
    }


    // Send message button click handler
    document.addEventListener("click", function(e) {
        if (e.target.closest(".send-message")) {
            let edit_message_id = DOM_API.getEditedMessageId();
            let message = DOM_API.getEnteredText();
            onSubmitMessage(message, edit_message_id);
        }
    });

    // Enter key to send message (and ArrowUp to edit last message)
    document.addEventListener("keydown", function(e) {
        if (e.target.id !== "message-input") return;

        if (e.keyCode == 13) {
            let edit_message_id = DOM_API.getEditedMessageId();
            let message = DOM_API.getEnteredText();
            onSubmitMessage(message, edit_message_id);
        }

        if (e.key == "ArrowUp") {
            // up arrow will move caret to start by default
            e.preventDefault();
            let message = DOM_API.getLatestOwnMessage();
            let message_id = message ? message.dataset.messageId : null;
            if (!DOM_API.isEditing()) {
                DOM_API.setEditing(message_id);
            }
        }
    });

    // Image click to open in lightbox
    document.addEventListener('click', function(e) {
        const container = e.target.closest('.attachment-image-container');
        if (container) {
            let srcs = [];
            const imgs = $$("img", container);
            for (let img of imgs) {
                srcs.push(img.src);
            }
            DOM_API.openBigImage(srcs);
        }
    });

    // Notification toggle switch
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.notif-switch');
        if (btn) {
            const currentState = btn.dataset.enabled === "true" || btn.dataset.enabled === true;
            const newState = !currentState;

            // Update UI immediately for instant feedback
            btn.dataset.enabled = newState;
            const icon = $("i", btn);
            if (icon) {
                if (newState) {
                    icon.classList.remove("fa-bell-slash");
                    icon.classList.add("fa-bell");
                } else {
                    icon.classList.remove("fa-bell");
                    icon.classList.add("fa-bell-slash");
                }
            }

            onToggleNotifications(btn.dataset.roomId, newState);
        }
    });

    // Escape key to cancel editing
    document.addEventListener('keydown', function(e) {
        if (e.key !== "Escape") {
            return;
        }

        if (!DOM_API.isEditing()) {
            return;
        }

        DOM_API.stopEditing();
    });

    // Delete images preview button
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.delete-images-preview');
        if (btn) {
            let room_id = btn.dataset.roomId;
            DOM_API.clearFiles(room_id);
        }
    });

    // Copy room link button
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.copy-room-url');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            let room_id = btn.dataset.roomId;
            copyRoomLink(room_id, btn);
        }
    });

    // Copy message link button
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.copy-message-url');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            let room_id = btn.dataset.roomId;
            let message_id = btn.dataset.messageId;
            copyMessageLink(room_id, message_id, btn);
        }
    });

    // File input change handler for image previews
    document.addEventListener("change", function(e) {
        if (!e.target.classList.contains("file-input")) return;

        let files = e.target.files;
        let preview_container = DOM_API.getPreviewDiv();

        // If editing, keep existing attachments and append new ones
        if (!DOM_API.isEditing() && preview_container) {
            preview_container.innerHTML = '';
        }

        if (files.length > 0) {
            const container = DOM_API.getPreviewContainer();
            if (container) {
                container.style.display = '';
            }
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
            if (preview_container) {
                preview_container.insertAdjacentHTML('beforeend', img_html);
            }

            fr.onload = function(e) {
                const imgEl = document.getElementById(preview_id);
                if (imgEl) {
                    imgEl.src = this.result;
                }
            };

            fr.readAsDataURL(file);
        }
    });

    // Vote button click handler
    document.addEventListener("click", function(e) {
        const btn = e.target.closest(".msg-vote");
        if (btn) {
            let event_type = btn.dataset.eventName; // upvote / downvote
            let message_id = btn.dataset.messageId;

            // if is active and pressed it means vote has to be removed
            let is_add = !btn.classList.contains('active');

            onUpdateVote.call(btn, event_type, message_id, is_add);
        }
    });

    // Show message history button
    document.addEventListener("click", function(e) {
        const btn = e.target.closest(".show-history");
        if (btn) {
            let message_id = btn.dataset.messageId;
            onMessageHistory(message_id);
        }
    });

    // Edit message button
    document.addEventListener("click", function(e) {
        const btn = e.target.closest(".edit-message");
        if (btn) {
            let message_id = btn.dataset.messageId;
            DOM_API.setEditing(message_id);
        }
    });

    // Remove existing attachment during editing
    document.addEventListener("click", function(e) {
        const btn = e.target.closest(".remove-existing-attachment");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            let filename = btn.dataset.filename;
            DOM_API.addRemovedAttachment(filename);
            const wrapper = btn.closest('.image-preview-wrapper');
            if (wrapper) {
                wrapper.remove();
            }

            // Hide preview container if no images left
            if (DOM_API.getPreviewDiv() && DOM_API.getPreviewDiv().children.length === 0) {
                const container = DOM_API.getPreviewContainer();
                if (container) {
                    container.style.display = 'none';
                }
            }
        }
    });

    // Remove new attachment before upload
    document.addEventListener("click", function(e) {
        const btn = e.target.closest(".remove-new-attachment");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            const wrapper = btn.closest('.image-preview-wrapper');
            if (wrapper) {
                wrapper.remove();
            }

            // Clear file input if no new attachments left
            const previewDiv = DOM_API.getPreviewDiv();
            if (previewDiv && $$('.new-attachment', previewDiv).length === 0) {
                const fileInput = DOM_API.getFileInput();
                if (fileInput) {
                    fileInput.value = "";
                }
            }

            // Hide preview container if no images left
            if (previewDiv && previewDiv.children.length === 0) {
                const container = DOM_API.getPreviewContainer();
                if (container) {
                    container.style.display = 'none';
                }
            }
        }
    });

    // Room join/leave (touch support for mobile)
    document.addEventListener('click', function(e) {
        handleRoomNameClick(e);
    });

    document.addEventListener('touchstart', function(e) {
        handleRoomNameClick(e);
    }, { passive: false });

    function handleRoomNameClick(e) {
        const roomName = e.target.closest('.room-name');
        if (!roomName) return;

        // Prevent default to avoid double-tap zoom on mobile
        if (e.type === 'touchstart') {
            e.preventDefault();
        }

        let room_id = roomName.parentElement.getAttribute("data-room-id");

        if (roomName.classList.contains("joined")) {
            // ignore second click on active room
            //onRoomTryLeave(true);
        } else {
            // Add visual feedback immediately
            roomName.parentElement.classList.add('room-tapping');
            // Remove feedback after a short delay
            setTimeout(() => {
                roomName.parentElement.classList.remove('room-tapping');
            }, 300);

            // Join room
            onRoomTryJoin(room_id);
        }
    }
});

/**
 * Simple slideToggle implementation as a vanilla JS replacement for jQuery
 * @param {Element} element - Element to toggle
 * @param {number} duration - Animation duration in ms
 */
function slideToggle(element, duration) {
    const isHidden = element.style.display === 'none' || getComputedStyle(element).display === 'none';
    element.style.overflow = 'hidden';

    if (isHidden) {
        element.style.display = 'block';
        element.style.height = '0';
        const targetHeight = element.scrollHeight;
        animate(element, { height: targetHeight + 'px' }, duration);
    } else {
        const currentHeight = element.scrollHeight;
        element.style.height = currentHeight + 'px';
        animate(element, { height: '0' }, duration, function() {
            element.style.display = 'none';
            element.style.height = '';
            element.style.overflow = '';
        });
    }
}

/**
 * Simple animation helper
 * @param {Element} element - Element to animate
 * @param {Object} properties - CSS properties to animate to
 * @param {number} duration - Duration in ms
 * @param {Function} [callback] - Callback when done
 */
function animate(element, properties, duration, callback) {
    element.style.transition = '';
    for (const prop in properties) {
        element.style.transition = `height ${duration}ms ease`;
        element.style[prop] = properties[prop];
    }

    const onTransitionEnd = function() {
        element.removeEventListener('transitionend', onTransitionEnd);
        if (callback) {
            callback();
        }
    };

    element.addEventListener('transitionend', onTransitionEnd);
}