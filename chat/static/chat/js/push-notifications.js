/**
 * @file
 * Push Notification Manager for Chat
 * Supports WebPush (browsers), FCM (Android), and APNS (iOS)
 * Provides comprehensive push notification handling including registration,
 * permissions, service worker management, and device lifecycle.
 */

/**
 * Push Notification Manager object
 * Manages all aspects of push notifications including platform detection,
 * registration, permissions, and lifecycle events.
 * @namespace
 */
const PushNotificationManager = {
    /**
     * Whether the manager has been initialized
     * @type {boolean}
     */
    isInitialized: false,

    /**
     * Array of supported platform names
     * @type {Array<'webpush'|'fcm'|'apns'>}
     */
    supportedPlatforms: [],

    /**
     * Currently active notification platform
     * @type {'webpush'|'fcm'|'apns'|null}
     */
    currentPlatform: null,

    /**
     * Registered device ID from server
     * @type {string|null}
     */
    registrationId: null,

    /**
     * Whether push notifications are currently enabled
     * @type {boolean}
     */
    isEnabled: false,

    /**
     * Detects available push notification platforms in the current browser
     * @returns {Object} - Platform detection results
     * @returns {boolean} returns.webpush - WebPush support status
     * @returns {boolean} returns.fcm - FCM support status (Firebase)
     * @returns {boolean} returns.apns - APNS support status (Safari/iOS)
     */
    detectPlatform() {
        const platform = {
            webpush: 'Notification' in window && 'serviceWorker' in navigator,
            fcm: false, // Will be detected after Firebase init
            apns: 'Notification' in window && 'serviceWorker' in navigator && navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome')
        };

        this.supportedPlatforms = Object.keys(platform).filter(key => platform[key]);
        return platform;
    },

    /**
     * Initialize push notification system
     * Detects platform and initializes appropriate notification handler
     * @async
     * @returns {Promise<boolean>} - true if notifications enabled successfully, false otherwise
     */
    async initialize() {
        if (this.isInitialized) {
            console.log('PushNotificationManager already initialized');
            return this.isEnabled;
        }

        // console.log('Initializing PushNotificationManager...');
        const platform = this.detectPlatform();

        // Request permission for WebPush
        if (platform.webpush) {
            this.currentPlatform = 'webpush';
            await this.initWebPush();
        } else if (platform.apns) {
            this.currentPlatform = 'apns';
            await this.initAPNS();
        } else {
            console.warn('No supported push notification platform detected');
            return false;
        }

        this.isInitialized = true;
        return this.isEnabled;
    },

    /**
     * Initialize WebPush (VAPID) notifications
     * Registers service worker, requests permissions, and subscribes to push
     * @async
     * @private
     * @returns {Promise<boolean>} - true if WebPush initialized successfully, false otherwise
     */
    async initWebPush() {
        try {
            // Check if Notification is supported
            if (!('Notification' in window)) {
                console.warn('Web Push notifications are not supported in this browser');
                return false;
            }

            // Register service worker FIRST (needed for PWA and push notifications)
            // This happens regardless of notification permission to enable PWA functionality
            if (!navigator.serviceWorker.controller) {
                // Register service worker (use /sw.js - scoped to /)
                const registration = await navigator.serviceWorker.register('/sw.js',{scope:"/"});
                // console.log('Service Worker registered, waiting for activation...');

                // Wait for service worker to become active with shorter timeout
                await this.waitForServiceWorkerActive(registration, 3000);
                // console.log('Service Worker is now active');
            } else {
                // console.log('Using existing active Service Worker');
            }

            // Get the active registration (navigator.serviceWorker.ready ensures SW is active)
            const swRegistration = await navigator.serviceWorker.ready;
            // console.log('Service Worker ready:', swRegistration);

            // Check notification permission - if not granted, we can't enable push notifications
            if (Notification.permission !== 'granted') {
                console.log('Service Worker registered, but notification permission not granted');
                // console.log('Permission status:', Notification.permission);
                this.isEnabled = false;
                return false;
            }

            let vapidPublicKey = window.VAPID_PUBLIC_KEY || '';
            if (!vapidPublicKey || vapidPublicKey.trim() === '') {
                console.error('VAPID public key is empty or missing. Please set VAPID_PUBLIC_KEY in your .env file.');
                this.isEnabled = false;
                return false;
            }

            const subscription = await swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: vapidPublicKey
            });

            // console.log('Push subscription obtained:', subscription);

            // Send subscription to server
            await this.registerDevice('webpush', subscription);

            this.isEnabled = true;
            return true;
        } catch (error) {
            console.error('Error initializing WebPush:', error);
            // Log more details about the error
            if (error.name === 'InvalidAccessError') {
                console.error('InvalidAccessError: The vapidPublicKey is invalid or malformed.');
            }
            console.error('Full error object:', error);
            this.isEnabled = false;
            return false;
        }
    },

    /**
     * Wait for service worker to become active
     * @async
     * @private
     * @param {ServiceWorkerRegistration} registration - Service worker registration
     * @param {number} timeout - Timeout in milliseconds (default 5000)
     * @returns {Promise<void>}
     */
    async waitForServiceWorkerActive(registration, timeout = 3000) {
        return new Promise((resolve, reject) => {
            // If already has controller, it's active
            if (navigator.serviceWorker.controller) {
                console.log('Service Worker already active');
                resolve();
                return;
            }

            // Wait for controllerchange event (SW became active)
            const controllerChangeListener = () => {
                console.log('Service Worker became active (controllerchange)');
                navigator.serviceWorker.removeEventListener('controllerchange', controllerChangeListener);
                clearTimeout(timeoutId);
                resolve();
            };

            navigator.serviceWorker.addEventListener('controllerchange', controllerChangeListener);

            // Also check registration.state periodically
            const checkState = () => {
                if (registration.installing) {
                    console.log('SW state: installing');
                } else if (registration.waiting) {
                    console.log('SW state: waiting');
                } else if (registration.active) {
                    console.log('SW state: active');
                }
            };

            // Check state immediately and periodically
            checkState();
            const stateInterval = setInterval(checkState, 500);

            // Also check periodically if controller exists (additional safety)
            const checkController = setInterval(() => {
                if (navigator.serviceWorker.controller) {
                    console.log('Service Worker detected as active via controller');
                    clearInterval(stateInterval);
                    clearInterval(checkController);
                    navigator.serviceWorker.removeEventListener('controllerchange', controllerChangeListener);
                    resolve();
                }
            }, 100);

            // Timeout fallback - check if registration became active
            const timeoutId = setTimeout(() => {
                console.log(`Service Worker activation timeout after ${timeout}ms`);
                console.log(`Final SW state: ${registration.state}`);
                clearInterval(stateInterval);
                clearInterval(checkController);
                navigator.serviceWorker.removeEventListener('controllerchange', controllerChangeListener);

                // If still no controller but registration is active, try to use it anyway
                if (registration.active && !navigator.serviceWorker.controller) {
                    // console.log('Registration is active but no controller - forcing activation');
                    // Calling skipWaiting may help
                    if (registration.waiting) {
                        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                    }
                }

                // Resolve anyway to continue the flow
                resolve();
            }, timeout);
        });
    },

    /**
     * APNS initialization (Safari/iOS)
     * @async
     * @private
     * @returns {Promise<boolean>} - true if APNS initialized successfully, false otherwise
     */
    async initAPNS() {
        try {
            // Safari uses a different API for push notifications
            // Note: APNS for web requires Apple Developer account and specific setup

            // For now, fall back to WebPush if available
            if (this.supportedPlatforms.includes('webpush')) {
                console.log('Falling back to WebPush for Safari');
                this.currentPlatform = 'webpush';
                return this.initWebPush();
            }

            console.warn('APNS web push not configured');
            this.isEnabled = false;
            return false;

        } catch (error) {
            console.error('Error initializing APNS:', error);
            this.isEnabled = false;
            return false;
        }
    },

    /**
     * FCM initialization (Firebase Cloud Messaging)
     * @async
     * @private
     * @returns {Promise<boolean>} - true if FCM initialized successfully, false otherwise
     */
    async initFCM() {
        try {
            // Check if Firebase is loaded
            if (typeof firebase === 'undefined') {
                console.warn('Firebase SDK not loaded');
                return false;
            }

            // Initialize Firebase if not already done
            if (!firebase.apps.length) {
                // Firebase config should be provided by Django template
                const firebaseConfig = window.FIREBASE_CONFIG || {};
                firebase.initializeApp(firebaseConfig);
            }

            // Get FCM token
            const messaging = firebase.messaging();
            const token = await messaging.getToken({
                vapidKey: window.FCM_VAPID_KEY // Optional for web
            });

            if (!token) {
                console.warn('FCM token retrieval failed');
                return false;
            }

            // Send token to server
            await this.registerDevice('fcm', token, 'Firebase');

            // Set up foreground message handler
            messaging.onMessage((payload) => {
                console.log('FCM foreground message:', payload);
                this.showNotification(payload.notification);
            });

            this.isEnabled = true;
            this.currentPlatform = 'fcm';
            console.log('FCM initialized successfully');
            return true;

        } catch (error) {
            console.error('Error initializing FCM:', error);
            return false;
        }
    },

    /**
     * Register device with server
     * @async
     * @private
     * @param {'webpush'|'fcm'|'apns'} platform - Platform name
     * @param {PushSubscription|string} registration - Push subscription or token
     * @param {string} [deviceType=''] - Device type identifier
     * @returns {Promise<Object|null>} - Server response on success, null on failure
     */
    async registerDevice(platform, registration, deviceType = '') {
        try {
            const registrationJson = registration.toJSON ? registration.toJSON() : registration;
            const p256dh = registrationJson.keys?.p256dh || '';
            const auth = registrationJson.keys?.auth || '';
            const response = await fetch('/chat/api/push/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    platform: platform,
                    registration_id: registration.endpoint || registration,
                    device_type: deviceType,
                    p256dh: p256dh,
                    auth: auth
                })
            });
            const data = await response.json();

            if (response.ok && data.success) {
                this.registrationId = data.device_id;
                console.log(`Device registered successfully: ${platform}`, data);
                return data;
            } else {
                console.error('Device registration failed:', data);
                return null;
            }

        } catch (error) {
            console.error('Error registering device:', error);
            return null;
        }
    },

    /**
     * Unregister device from server
     * @async
     * @param {'webpush'|'fcm'|'apns'} platform - Platform name
     * @param {string} registrationId - Device registration ID
     * @returns {Promise<Object|null>} - Server response on success, null on failure
     */
    async unregisterDevice(platform, registrationId) {
        try {
            const response = await fetch('/chat/api/push/unregister/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    platform: platform,
                    registration_id: registrationId
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                console.log(`Device unregistered: ${platform}`, data);
                return data;
            } else {
                console.error('Device unregistration failed:', data);
                return null;
            }

        } catch (error) {
            console.error('Error unregistering device:', error);
            return null;
        }
    },

    /**
     * Display a push notification
     * Shows notification using Web Push API or basic Notification constructor
     * @param {Object} notification - Notification data
     * @param {string} notification.title - Notification title
     * @param {string} notification.body - Notification body text
     * @param {string} [notification.icon] - URL to notification icon
     * @param {string} [notification.badge] - URL to notification badge
     * @param {Object} [notification.data] - Additional data (room_id, click_action, url)
     * @returns {Notification|null} - Notification object if shown, null otherwise
     */
    showNotification(notification) {
        if (Notification?.permission !== 'granted')
            return;

        // Use Web Push API if available, otherwise use basic Notification
        if (this.currentPlatform === 'webpush' && this.registrationId) {
            // Notifications are handled by the service worker
            // This method is mainly for foreground notifications
        }

        const notif = new Notification(notification.title || 'Chat Message', {
            body: notification.body || '',
            icon: notification.icon || '/favicon.ico',
            badge: notification.badge || '/favicon.ico',
            tag: `chat-${notification.room_id || 'general'}`,
            requireInteraction: true
        });

        if (notification.click_action) {
            notif.onclick = () => {
                window.location.href = notification.click_action;
                notif.close();
            };
        }
        return notif;
    },

    /**
     * Toggle notifications for a specific room
     * Sends request to server to enable/disable notifications for room
     * @async
     * @param {number} roomId - The room ID
     * @param {boolean} enabled - Whether to enable (true) or disable (false) notifications
     * @returns {Promise<boolean>} - true if server responded OK, false otherwise
     */
    async toggleRoomNotifications(roomId, enabled) {
        try {
            const response = await fetch('/chat/api/toggle-notifications/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    room_id: roomId,
                    enabled: enabled
                })
            });

            return response.ok;
        } catch (error) {
            console.error('Error toggling notifications:', error);
            return false;
        }
    },

    /**
     * Utility: Get CSRF token from cookies
     * @private
     * @returns {string} - CSRF token or empty string if not found
     */
    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) {
                return decodeURIComponent(value);
            }
        }
        return '';
    }
};

// Export for ES modules
export { PushNotificationManager };

// Initialize when DOM is ready (will be called from chat.js)
document.addEventListener('DOMContentLoaded', async function() {
    // Only initialize if user is on chat page
    const enabled = await PushNotificationManager.initialize();
    console.log('Push notifications enabled:', enabled);

    // Update UI based on notification state
    if (enabled) {
        document.body.classList.add('push-notifications-enabled');
    }
});