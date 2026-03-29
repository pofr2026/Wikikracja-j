/**
 * @file
 * WebSocket notification handling module.
 * Manages WebSocket connection for receiving real-time notifications
 * and handles displaying them to the user.
 */

import { makeNotification } from './utility.js';

/**
 * Handles incoming WebSocket notifications
 * @param {Object} notification - Notification data object
 * @param {string} notification.title - Notification title
 * @param {string} notification.body - Notification body text
 * @param {number} [notification.room_id] - Optional room ID associated with notification
 */
export function onReceiveNotification(notification) {
    makeNotification(notification);
}

/**
 * Handles room unsee events (marks room as having unread messages)
 * @param {number} room_id - The room ID to mark as unread
 */
export function onRoomUnsee(room_id) {
    $(".nav-link[data-route='chat']").addClass("chat-has-messages");
}

// Initialize WebSocket connection for notifications when DOM is ready
$(document).ready(function() {
    // Check if Notification API is supported
    if (!Notification) {
        // console.log("Connecting aborted in !Notification");
        return;
    }
    
    // Check if notification permission has been granted or user opted out
    if (Notification.permission !== 'granted' && localStorage.notifications !== "No") {
        // console.log("Connecting aborted in permission !==granted");
        return;
    }   
    
    // Determine WebSocket URL based on current protocol
    let ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    let ws_path = ws_scheme + '://' + window.location.host + "/chat/stream/";
    console.log("Connecting to " + ws_path);

    // Create WebSocket connection
    let socket = new ReconnectingWebSocket(ws_path);

    // Handle incoming messages
    socket.onmessage = (e) => {
        let data = JSON.parse(e.data);
        // console.log("Got websocket message ", data);

        // Handle errors
        if (data.error) {
            console.error(data.error);
            return;
        }

        if (data.notification) {
            let notif = data.notification;
            onReceiveNotification(notif);

        } else if (data.unsee_room) {
            onRoomUnsee(data.unsee_room);

        } else {
            //  console.log("Cannot handle message!");
        }
    }
});