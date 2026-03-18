/**
 * Push Notification Manager for Chat
 * Supports WebPush (browsers), FCM (Android), and APNS (iOS)
 */

// Push notification state
const PushNotificationManager = {
    isInitialized: false,
    supportedPlatforms: [],
    currentPlatform: null,
    registrationId: null,
    isEnabled: false,
    
    // Platform detection
    detectPlatform() {
        const platform = {
            webpush: 'Notification' in window && 'serviceWorker' in navigator,
            fcm: false, // Will be detected after Firebase init
            apns: 'Notification' in window && 'serviceWorker' in navigator && navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome')
        };
        
        this.supportedPlatforms = Object.keys(platform).filter(key => platform[key]);
        return platform;
    },
    
    // Initialize push notifications
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
    
    // WebPush initialization (VAPID)
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
                console.log('Service Worker registered, waiting for activation...');
                
                // Wait for service worker to become active with shorter timeout
                await this.waitForServiceWorkerActive(registration, 5000);
                console.log('Service Worker is now active');
            } else {
                console.log('Using existing active Service Worker');
            }
            
            // Get the active registration (navigator.serviceWorker.ready ensures SW is active)
            const swRegistration = await navigator.serviceWorker.ready;
            console.log('Service Worker ready:', swRegistration);
            
            // Check notification permission - if not granted, we can't enable push notifications
            if (Notification.permission !== 'granted') {
                console.log('Service Worker registered, but notification permission not granted');
                console.log('Permission status:', Notification.permission);
                this.isEnabled = false;
                return false;
            }
            
            let vapidPublicKey = window.VAPID_PUBLIC_KEY || '';
            if (!vapidPublicKey || vapidPublicKey.trim() === '') {
                console.error('VAPID public key is empty or missing. Please set VAPID_PUBLIC_KEY in your .env file.');
                this.isEnabled = false;
                return false;
            }
            
            // Convert VAPID key to Uint8Array
            // let convertedVapidKey;
            // try {
            //     convertedVapidKey = this.urlBase64ToUint8Array(vapidPublicKey);
                
            //     // VAPID public key MUST be exactly 65 bytes for P-256 (0x04 + 32-byte X + 32-byte Y)
            //     if (convertedVapidKey.length !== 65) {
            //         console.error(`Invalid VAPID key length: ${convertedVapidKey.length} bytes (expected 65 bytes)`);
            //         this.isEnabled = false;
            //         return false;
            //     }
                
            //     // Verify it starts with 0x04 (uncompressed point indicator)
            //     if (convertedVapidKey[0] !== 0x04) {
            //         console.error('Invalid VAPID key: first byte should be 0x04 (uncompressed point), got:', convertedVapidKey[0]);
            //         this.isEnabled = false;
            //         return false;
            //     }
            // } catch (conversionError) {
            //     console.error('Failed to convert VAPID key to Uint8Array:', conversionError);
            //     console.error('Key may be malformed. Ensure it is valid base64 or base64url encoded.');
            //     this.isEnabled = false;
            //     return false;
            // }            
            
            const subscription = await swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: vapidPublicKey
            });
            
            console.log('Push subscription obtained:', subscription);

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
    
    // Helper: Wait for service worker to become active
    async waitForServiceWorkerActive(registration, timeout = 5000) {
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
                console.warn(`Service Worker activation timeout after ${timeout}ms`);
                console.log(`Final SW state: ${registration.state}`);
                clearInterval(stateInterval);
                clearInterval(checkController);
                navigator.serviceWorker.removeEventListener('controllerchange', controllerChangeListener);
                
                // If still no controller but registration is active, try to use it anyway
                if (registration.active && !navigator.serviceWorker.controller) {
                    console.log('Registration is active but no controller - forcing activation');
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
    
    // // APNS initialization (Safari/iOS)
    // async initAPNS() {
    //     try {
    //         // Safari uses a different API for push notifications
    //         // Note: APNS for web requires Apple Developer account and specific setup
            
    //         // For now, fall back to WebPush if available
    //         if (this.supportedPlatforms.includes('webpush')) {
    //             console.log('Falling back to WebPush for Safari');
    //             this.currentPlatform = 'webpush';
    //             return this.initWebPush();
    //         }
            
    //         console.warn('APNS web push not configured');
    //         this.isEnabled = false;
    //         return false;
            
    //     } catch (error) {
    //         console.error('Error initializing APNS:', error);
    //         this.isEnabled = false;
    //         return false;
    //     }
    // },
    
    // // FCM initialization (Firebase Cloud Messaging)
    // async initFCM() {
    //     try {
    //         // Check if Firebase is loaded
    //         if (typeof firebase === 'undefined') {
    //             console.warn('Firebase SDK not loaded');
    //             return false;
    //         }
            
    //         // Initialize Firebase if not already done
    //         if (!firebase.apps.length) {
    //             // Firebase config should be provided by Django template
    //             const firebaseConfig = window.FIREBASE_CONFIG || {};
    //             firebase.initializeApp(firebaseConfig);
    //         }
            
    //         // Get FCM token
    //         const messaging = firebase.messaging();
    //         const token = await messaging.getToken({
    //             vapidKey: window.FCM_VAPID_KEY // Optional for web
    //         });
            
    //         if (!token) {
    //             console.warn('FCM token retrieval failed');
    //             return false;
    //         }
            
    //         // Send token to server
    //         await this.registerDevice('fcm', token, 'Firebase');
            
    //         // Set up foreground message handler
    //         messaging.onMessage((payload) => {
    //             console.log('FCM foreground message:', payload);
    //             this.showNotification(payload.notification);
    //         });
            
    //         this.isEnabled = true;
    //         this.currentPlatform = 'fcm';
    //         console.log('FCM initialized successfully');
    //         return true;
            
    //     } catch (error) {
    //         console.error('Error initializing FCM:', error);
    //         return false;
    //     }
    // },
    
    // Register device with server
    async registerDevice(platform, registration, deviceType = '') {
        try {
            const registrationJson = registration.toJSON();
            const p256dh = registrationJson.keys.p256dh;
            const auth = registrationJson.keys.auth;
            const response = await fetch('/chat/api/push/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    platform: platform,
                    registration_id: registration.endpoint,
                    device_type: deviceType,
                    p256dh: p256dh || '',
                    auth: auth || ''
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
    
    // Unregister device from server
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
    
    // Show notification
    showNotification(notification) {
        if (Notification.permission === 'granted') {
            // Use Web Push API if available, otherwise use basic Notification
            if (this.currentPlatform === 'webpush' && this.registrationId) {
                // Notifications are handled by the service worker
                // This method is mainly for foreground notifications
            }
            
            const notif = new Notification(notification.title || 'Chat Message', {
                body: notification.body || '',
                icon: notification.icon || '/static/favicon.ico',
                badge: notification.badge || '/static/favicon.ico',
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
        }
    },
    
    // Utility: Convert base64 or base64url string to Uint8Array for VAPID
    // Accepts both standard base64 (with +, /, =) and base64url (with -, _, no padding)
    // urlBase64ToUint8Array(base64String) {
    //     try {
    //         // Remove any whitespace
    //         let base64 = base64String.trim();
            
    //         // Convert base64url to base64 if needed (replace URL-safe characters)
    //         // This handles both formats: if already standard base64, these replacements do nothing
    //         base64 = base64.replace(/-/g, '+').replace(/_/g, '/');
            
    //         // Add padding if needed (base64 length must be multiple of 4)
    //         const padding = '='.repeat((4 - base64.length % 4) % 4);
    //         base64 = base64 + padding;
            
    //         // Decode base64 to binary string
    //         const rawData = window.atob(base64);
    //         const outputArray = new Uint8Array(rawData.length);
            
    //         for (let i = 0; i < rawData.length; ++i) {
    //             outputArray[i] = rawData.charCodeAt(i);
    //         }
            
    //         return outputArray;
    //     } catch (error) {
    //         console.error('urlBase64ToUint8Array error:', error);
    //         console.error('Input key:', base64String);
    //         throw error; // Re-throw to be caught by caller
    //     }
    // },
    
    // Utility: Get CSRF token from cookie
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
    },
    
    // Toggle notifications for a room (muted_by logic still in DB)
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