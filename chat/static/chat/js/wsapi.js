/**
 * @file
 * WebSocket API module for chat communication.
 * Provides a high-level interface for real-time chat operations
 * including sending messages, joining rooms, voting, and file uploads.
 */

import { onSocketMessage } from './handlers.js';

/**
 * WebSocket API class for managing chat WebSocket connection
 * Handles all server communication through WebSocket protocol
 * @class
 */
export default class WsApi {
    /**
     * Constructs a new WsApi instance
     * Creates WebSocket connection and sets up message handlers
     */
    constructor() {
        this.promises = {};

        // Correctly decide between ws:// and wss://
        let ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
        let ws_path = ws_scheme + '://' + window.location.host + "/chat/stream/";
        console.log("Connecting to " + ws_path);

        this.socket = new ReconnectingWebSocket(ws_path);

        $(window).on('beforeunload', () => {            
            console.log("beforeunload: Closing connecton " + ws_path);
            this.socket.close();
        });

        this.socket.onmessage = (e) => {
            let data = JSON.parse(e.data);

            if (data.__TRACE_ID) {
                if (data.error) {
                    this.rejectAsync(data);
                } else {
                    this.receiveAsync(data);
                }
            } else {
                if (data.error) {
                    alert(data.error);
                } else {
                    onSocketMessage(data);
                }
            }
        }

        // Helpful debugging
        this.socket.onopen = function() {
            console.log("Connected to chat socket");
            this.wsOnConnect();
        }.bind(this);

        this.socket.onclose = function() {
            console.log("Disconnected from chat socket");
            this.wsOnDisconnect();
        }.bind(this);
    }

    /**
     * Called when WebSocket connection is established
     * Override in subclass to add custom initialization
     */
    async wsOnConnect() {
    }

    /**
     * Called when WebSocket connection is closed
     * Override in subclass to handle disconnection
     */
    async wsOnDisconnect() {
    }

    /**
     * Sends a JSON message over WebSocket (no response expected)
     * @param {Object} obj - Object to send (will be JSON stringified)
     */
    sendJson(obj) {
        this.socket.send(JSON.stringify(obj));
    }

    /**
     * Sends a JSON message and waits for response
     * Uses __TRACE_ID to correlate request/response
     * @param {Object} obj - Object to send
     * @returns {Promise<Object>} - Promise resolving to server response
     */
    async sendJsonAsync(obj) {
        let ID = Math.floor(Math.random() * 1000000) + 1;
        obj.__TRACE_ID = ID;
        let promises = this.promises;

        let promise = new Promise(
            (resolve, reject) => {
                promises[ID] = {
                    resolve,
                    reject
                }
            }
        );

        this.sendJson(obj);
        return promise;
    }

    /**
     * Handles successful async response from server
     * @param {Object} obj - Response object with __TRACE_ID
     */
    receiveAsync(obj) {
        let ID = obj.__TRACE_ID;
        if (this.promises[ID] === undefined) {
            console.warn("received __TRACE_ID of " + ID + " that does not exist locally. Was it already resolved? Server should return only one message from this kind of responding handlers");
            return;
        }
        this.promises[ID].resolve(obj);
        delete this.promises[ID];
    }

    /**
     * Handles error response from server
     * @param {Object} obj - Error object with __TRACE_ID and error message
     */
    rejectAsync(obj) {
        let ID = obj.__TRACE_ID;
        if (this.promises[ID] === undefined) {
            alert(obj.error);
            return;
        }
        this.promises[ID].reject(obj.error);
        delete this.promises[ID];
    }

    /**
     * Joins a chat room
     * @param {number} room_id - ID of the room to join
     * @returns {Promise<Object>} - Room data from server
     */
    async joinRoom(room_id) {
        return await this.sendJsonAsync({
            command: "join",
            room_id: room_id
        });
    }

    /**
     * Notifies server that room has been seen
     * @param {number} room_id - ID of room that was viewed
     */
    seenRoom(room_id) {
        this.sendJson({
            command: "room-seen",
            room_id: room_id
        });
    }

    /**
     * Sends a chat message to the current room
     * @param {number} room_id - ID of the room
     * @param {string} message - Message text content
     * @param {boolean} is_anonymous - Whether to send as anonymous
     * @param {Object} attachments - Attachment data (images array)
     */
    sendMessage(room_id, message, is_anonymous, attachments) {
        this.sendJson({
            command: "send",
            room_id, // room number
            message, // value, message to send
            is_anonymous,
            attachments
        });
    }

    /**
     * Edits an existing message
     * @param {number} message_id - ID of message to edit
     * @param {string} message - New message text
     * @param {Object} attachments - New attachments (images array)
     * @param {Array<string>} removed_attachments - Filenames to remove
     * @param {string|null} original_message - Original message text for comparison
     */
    editMessage(message_id, message, attachments = {}, removed_attachments = [], original_message = null) {
        let payload = {
            command: "edit-message",
            message_id: message_id
        };
        
        // Only include new_message if it changed
        if (original_message === null || message !== original_message) {
            payload.new_message = message;
        }
        
        // Add attachments if provided
        if (attachments && Object.keys(attachments).length > 0) {
            payload.attachments = attachments;
        }
        
        // Add removed attachments if provided
        if (removed_attachments && removed_attachments.length > 0) {
            payload.removed_attachments = removed_attachments;
        }
        
        this.sendJson(payload);
    }

    /**
     * Adds an upvote or downvote to a message
     * @param {string} vote - Vote type ('upvote' or 'downvote')
     * @param {number} message_id - ID of message to vote on
     */
    addVote(vote, message_id) {
        this.sendJson({
            command: "message-add-vote",
            vote: vote,
            message_id: message_id
        });
    }

    /**
     * Removes a vote from a message
     * @param {string} vote - Vote type ('upvote' or 'downvote')
     * @param {number} message_id - ID of message to remove vote from
     */
    removeVote(vote, message_id) {
        this.sendJson({
            command: "message-remove-vote",
            vote: vote,
            message_id: message_id
        });
    }

    /**
     * Leaves the current chat room
     * @param {number} room_id - ID of room to leave
     * @returns {Promise<Object>} - Server response
     */
    async leaveRoom(room_id) {
        return await this.sendJsonAsync({
            command: "leave",
            room_id: room_id
        });
    }

    /**
     * Requests list of online users
     * @returns {Promise<Object>} - Online users data
     */
    async getOnlineUsers() {
        return await this.sendJsonAsync({
            command: "get-online-users"
        });
    }

    /**
     * Fetches edit history for a message
     * @param {number} message_id - ID of message
     * @returns {Promise<Object>} - Message history data
     */
    async getMessageHistory(message_id) {
        return await this.sendJsonAsync({
            command: "get-message-history",
            message_id: message_id,
        });
    }

    /**
     * Requests notification data (rooms with notifications enabled)
     * @returns {Promise<Object>} - Notification settings data
     */
    async getNotificationData() {
        return await this.sendJsonAsync({
            command: 'get-notifications-data'
        });
    }

    /**
     * Uploads files to the server
     * @param {FileList} files - Files to upload
     * @returns {Promise<Object>} - Upload response with filenames
     */
    async uploadFiles(files) {
        if (files.length == 0) {
            return new Promise((r, _) => r({ 'filenames': [] }));
        }

        let xhr = new XMLHttpRequest();
        let formData = new FormData();

        let promise_funcs = {};

        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4 && xhr.status == 200) {
                promise_funcs.resolve(JSON.parse(xhr.responseText))
            }
        };

        let promise = new Promise((resolve, reject) => {
            promise_funcs.resolve = resolve;
            promise_funcs.reject = reject;
        });

        xhr.open("POST", "upload/", true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        for (let i = 0; i < files.length; ++i) {
            let file = files.item(i);
            let name = file.name;
            let size = file.size;
            if (size > 10000000) {
                alert("file is too big");
                continue;
            }
            formData.append("images", file);
        }
        xhr.send(formData);
        return promise;
    }

    /**
     * Toggles push notifications for a room
     * @param {number} room_id - ID of the room
     * @param {boolean} enabled - Whether to enable notifications
     */
    toggleNotifications(room_id, enabled) {
        this.sendJson({
            command: 'toggle-notifications',
            room_id,
            enabled
        });
    }
}