/**
 * @file
 * Shared WebSocket connection manager.
 * Provides a singleton WebSocket instance that can be used by multiple modules.
 * Handles connection lifecycle, message routing, and async request/response patterns.
 */

let sharedWebSocketInstance = null;
let messageHandlers = [];

/**
 * Get the singleton WebSocket manager instance
 * Creates connection if it doesn't exist yet
 * @returns {Object} WebSocket manager with methods for messaging and handlers
 */
export function getSharedWebSocket() {
    if (sharedWebSocketInstance === null) {
        sharedWebSocketInstance = createWebSocketManager();
    }
    return sharedWebSocketInstance;
}

/**
 * Creates a new WebSocket manager with connection and message handling
 * @private
 * @returns {Object} WebSocket manager object
 */
function createWebSocketManager() {
    let promises = {};
    let socketMessageHandler = null;
    let wsOnConnect = null;
    let wsOnDisconnect = null;

    // Determine WebSocket URL based on current protocol
    let ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
    let ws_path = ws_scheme + '://' + window.location.host + "/chat/stream/";
    console.log("Connecting to " + ws_path);

    // Create WebSocket connection
    let socket = new ReconnectingWebSocket(ws_path);

    /**
     * Main message handler for all incoming WebSocket messages
     * Routes messages to appropriate handlers based on content
     * @param {Object} data - Parsed JSON message from server
     */
    socket.onmessage = (e) => {
        let data;
        try {
            data = JSON.parse(e.data);
        } catch (err) {
            console.error("Failed to parse WebSocket message:", err);
            return;
        }

        // Handle errors
        if (data.error) {
            console.error(data.error);
        }

        // Route TRACE_ID messages to async promise resolution/rejection
        if (data.__TRACE_ID) {
            if (data.error) {
                rejectAsync(data, promises);
            } else {
                receiveAsync(data, promises);
            }
            return;
        }

        // For non-TRACE messages, use the main handler if set
        if (socketMessageHandler) {
            socketMessageHandler(data);
        } else {
            // If no main handler, broadcast to all registered handlers
            broadcastToHandlers(data);
        }
    };

    socket.onopen = function() {
        //console.log("Connected to socket");
        if (wsOnConnect) {
            wsOnConnect();
        }
    }.bind(this);

    socket.onclose = function() {
        console.log("Disconnected from socket");
        if (wsOnDisconnect) {
            wsOnDisconnect();
        }
    }.bind(this);

    // Set up beforeunload handler to close socket
    window.addEventListener('beforeunload', () => {
        console.log("beforeunload: Closing connection " + ws_path);
        socket.close();
    });

    /**
     * Broadcasts a message to all registered handlers
     * @param {Object} data - Message data
     */
    function broadcastToHandlers(data) {
        for (let handler of messageHandlers) {
            try {
                handler(data);
            } catch (err) {
                console.error("Error in message handler:", err);
            }
        }
    }

    /**
     * Resolves a pending promise with async response data
     * @param {Object} obj - Response object with __TRACE_ID
     * @param {Object} promises - Promise registry
     */
    function receiveAsync(obj, promises) {
        let ID = obj.__TRACE_ID;
        if (promises[ID] === undefined) {
            console.warn("received __TRACE_ID of " + ID + " that does not exist locally");
            return;
        }
        promises[ID].resolve(obj);
        delete promises[ID];
    }

    /**
     * Rejects a pending promise with error data
     * @param {Object} obj - Error object with __TRACE_ID and error message
     * @param {Object} promises - Promise registry
     */
    function rejectAsync(obj, promises) {
        let ID = obj.__TRACE_ID;
        if (promises[ID] === undefined) {
            alert(obj.error);
            return;
        }
        promises[ID].reject(obj.error);
        delete promises[ID];
    }

    return {
        /**
         * Raw WebSocket instance (use with caution)
         */
        socket: socket,

        /**
         * Set the main message handler for non-TRACE messages
         * Only one main handler can be set at a time
         * @param {Function} handler - Function to call with message data
         */
        setSocketMessageHandler: function(handler) {
            socketMessageHandler = handler;
        },

        /**
         * Add a message handler that receives all non-TRACE messages
         * Multiple handlers can be registered
         * @param {Function} handler - Function to call with message data
         */
        addMessageHandler: function(handler) {
            messageHandlers.push(handler);
        },

        /**
         * Remove a previously registered message handler
         * @param {Function} handler - Handler to remove
         */
        removeMessageHandler: function(handler) {
            let index = messageHandlers.indexOf(handler);
            if (index > -1) {
                messageHandlers.splice(index, 1);
            }
        },

        /**
         * Set callback for WebSocket connection open event
         * @param {Function} handler - Function to call on connection
         */
        setOnConnect: function(handler) {
            wsOnConnect = handler;
        },

        /**
         * Set callback for WebSocket connection close event
         * @param {Function} handler - Function to call on disconnection
         */
        setOnDisconnect: function(handler) {
            wsOnDisconnect = handler;
        },

        /**
         * Send a JSON message over WebSocket (no response expected)
         * @param {Object} obj - Object to send (will be JSON stringified)
         */
        sendJson: function(obj) {
            socket.send(JSON.stringify(obj));
        },

        /**
         * Send a JSON message and wait for response
         * Uses __TRACE_ID to correlate request/response
         * @param {Object} obj - Object to send
         * @returns {Promise<Object>} - Promise resolving to server response
         */
        sendJsonAsync: function(obj) {
            let ID = Math.floor(Math.random() * 1000000) + 1;
            obj.__TRACE_ID = ID;

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
    };
}