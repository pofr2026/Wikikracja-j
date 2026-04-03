/**
 * @file
 * Service Worker for Chat WebPush Notifications
 * Handles push notifications, caches static assets, and manages offline functionality.
 * 
 * This service worker:
 * - Caches static assets for offline use
 * - Handles push notification events
 * - Handles notification click events
 * - Manages subscription changes
 * - Communicates with main thread via postMessage
 */

// Cache names
const CACHE_NAME = 'chat-push-v1';
const STATIC_CACHE = 'chat-static-v1';

/**
 * Install event handler - caches static assets
 * @param {ExtendableEvent} event - Install event object
 */
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('Caching static assets');
                return cache.addAll([
                    './',
                    // '/static/chat/js/jquery-4.0.0.min.js',
                    // '/static/chat/js/notifications.js',
                    // '/static/chat/js/push-notifications.js',
                    // '/static/chat/js/reconnecting-websocket.js',
                    // '/static/chat/js/chat.js',
                    // '/static/chat/js/ejs.min.js',
                    // '/static/chat/js/utility.js',
                    // '/favicon.ico',
                ]);
            })
    );
    self.skipWaiting();
});

/**
 * Activate event handler - cleans up old caches
 * @param {ExtendableEvent} event - Activate event object
 */
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== STATIC_CACHE && cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

/**
 * Push notification event handler
 * Shows notification when push message is received
 * @param {PushEvent} event - Push event object
 */
self.addEventListener('push', (event) => {
    console.log('Push event received:', event);
    
    let notificationData = {};
    
    if (event.data) {
        try {
            notificationData = event.data.json();
        } catch (e) {
            notificationData = {
                title: 'Chat Message',
                body: event.data.text(),
            };
        }
    }
    
    const title = notificationData.title || 'Chat Message';
    const options = {
        body: notificationData.body || '',
        icon: notificationData.icon || '/favicon.ico',
        badge: notificationData.badge || '/favicon.ico',
        vibrate: [200, 100, 200],
        requireInteraction: true,
        data: {
            room_id: notificationData.data?.room_id,
            click_action: notificationData.data?.click_action || '/chat',
            url: notificationData.data?.click_action || '/chat'
        },
        actions: [
            {
                action: 'open',
                title: 'Open'
            }
        ]
    };
    
    // Show notification
    const promiseChain = self.registration.showNotification(title, options);
    event.waitUntil(promiseChain);
});

/**
 * Notification click event handler
 * Opens or focuses the chat window when notification is clicked
 * @param {NotificationEvent} event - Notification click event object
 */
self.addEventListener('notificationclick', (event) => {
    console.log('Notification click received:', event);
    
    const action = event.action;
    const data = event.notification.data || {};
    const url = data.click_action || data.url || '/chat';
    
    if (action === 'dismiss' || action === 'close') {
        event.notification.close();
        return;
    }
    
    // Open or focus the window
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // If a window/tab with the URL is already open, focus it
            for (const client of clientList) {
                if (client.url === url && 'focus' in client) {
                    return client.focus();
                }
            }
            // Otherwise, open a new tab/window
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        }).then(() => {
            // Close the notification
            event.notification.close();
        })
    );
});

/**
 * Message event handler - communication with main thread
 * @param {MessageEvent} event - Message event object
 */
self.addEventListener('message', (event) => {
    console.log('Service Worker message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_SUBSCRIPTION') {
        self.registration.pushManager.getSubscription()
            .then((subscription) => {
                event.ports[0].postMessage({
                    subscription: subscription
                });
            });
    }
});

/**
 * Push subscription change event handler
 * Automatically resubscribes when subscription expires/changes
 * @param {PushSubscriptionChangeEvent} event - Subscription change event object
 */
self.addEventListener('pushsubscriptionchange', (event) => {
    console.log('Push subscription change detected:', event);
    
    if (event.oldSubscription)
        event.waitUntil(
            self.registration.pushManager.subscribe(event.oldSubscription.options)
                .then((newSubscription) => {
                    console.log('New subscription obtained:', newSubscription);
                    // Send new subscription to server
                    return fetch('/chat/api/push/register/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            platform: 'webpush',
                            registration_id: newSubscription,
                            device_type: 'service-worker'
                        })
                    });
                })
                .catch((error) => {
                    console.error('Failed to resubscribe after subscription change:', error);
                })
    );
});