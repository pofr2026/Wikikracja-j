/**
 * Main application JavaScript
 * Consolidates inline scripts from various templates
 */

// ============================================================
// Global notification permission banner handler - from base.html
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    const banner = document.getElementById('notification-permission-banner');
    const blockedBanner = document.getElementById('notification-blocked-banner');
    if (!banner || !blockedBanner) return;

    // Check if Notification API is supported
    if (!('Notification' in window)) {
        console.log('Notifications not supported');
        return;
    }

    console.log('Notification permission status:', Notification.permission);

    // Check if user has already dismissed the banner
    const dismissed = localStorage.getItem('notification-banner-dismissed');
    const blockedDismissed = localStorage.getItem('notification-blocked-dismissed');

    // Show appropriate banner based on permission state
    if (Notification.permission === 'default' && !dismissed) {
        banner.style.display = 'block';
    } else if (Notification.permission === 'denied' && !blockedDismissed) {
        blockedBanner.style.display = 'block';
    }

    // Handle "Enable Notifications" button
    document.getElementById('enable-notifications-global')?.addEventListener('click', async function(e) {
        e.preventDefault();
        console.log('Enable notifications clicked, current permission:', Notification.permission);

        try {
            // Request permission
            const permission = await Notification.requestPermission();
            console.log('Permission result:', permission);

            if (permission === 'granted') {
                banner.style.display = 'none';
                localStorage.removeItem('notification-banner-dismissed');
                // Reload to initialize push notifications
                location.reload();
            } else if (permission === 'denied') {
                // Show blocked banner
                banner.style.display = 'none';
                blockedBanner.style.display = 'block';
                // Remember that user denied
                localStorage.setItem('notification-blocked-dismissed', Date.now() + (30 * 24 * 60 * 60 * 1000));
            } else {
                // Permission is still 'default' - user dismissed the prompt
                console.log('User dismissed the permission prompt');
            }
        } catch (error) {
            console.error('Error requesting notification permission:', error);
            // Show blocked banner on error
            banner.style.display = 'none';
            blockedBanner.style.display = 'block';
        }
    });

    // Handle "Not now" button
    document.getElementById('dismiss-notifications-banner')?.addEventListener('click', function() {
        banner.style.display = 'none';
        // Remember dismissal for 7 days
        const dismissedUntil = Date.now() + (7 * 24 * 60 * 60 * 1000);
        localStorage.setItem('notification-banner-dismissed', dismissedUntil);
    });

    // Handle "Dismiss" button on blocked banner
    document.getElementById('dismiss-blocked-banner')?.addEventListener('click', function() {
        blockedBanner.style.display = 'none';
        // Remember dismissal for 30 days
        const dismissedUntil = Date.now() + (30 * 24 * 60 * 60 * 1000);
        localStorage.setItem('notification-blocked-dismissed', dismissedUntil);
    });

    // Check if dismissal has expired
    if (dismissed && parseInt(dismissed) < Date.now()) {
        localStorage.removeItem('notification-banner-dismissed');
        if (Notification.permission === 'default') {
            banner.style.display = 'block';
        }
    }

    if (blockedDismissed && parseInt(blockedDismissed) < Date.now()) {
        localStorage.removeItem('notification-blocked-dismissed');
        if (Notification.permission === 'denied') {
            blockedBanner.style.display = 'block';
        }
    }
});

// ============================================================
// Tab persistence for task list - from task_list.html
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    // Tab persistence: Check localStorage for last active tab
    const lastTab = localStorage.getItem('tasks_tab');
    if (lastTab) {
        const tabTrigger = document.querySelector(`[data-bs-target="#${lastTab}"]`);
        if (tabTrigger) {
            const tab = new bootstrap.Tab(tabTrigger);
            tab.show();
        }
    }

    // Save tab selection on tab change
    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target').substring(1);
            localStorage.setItem('tasks_tab', targetId);
        });
    });
});

// ============================================================
// Year selector for bookkeeping report - from report_list.html
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    const yearSelect = document.getElementById('yearSelect');
    if (yearSelect) {
        const reportListUrl = yearSelect.dataset.reportListUrl;
        yearSelect.addEventListener('change', function() {
            const selectedYear = this.value;
            window.location.href = reportListUrl + '?year=' + selectedYear;
        });
    }
});

// ============================================================
// Event form frequency toggle - from event_form.html
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    const frequencyField = document.getElementById('id_frequency');
    const ordinalFieldsRow = document.getElementById('ordinal-fields-row');

    if (frequencyField && ordinalFieldsRow) {
        function toggleOrdinalFields() {
            if (frequencyField.value === 'monthly_ordinal') {
                ordinalFieldsRow.style.display = 'flex';
            } else {
                ordinalFieldsRow.style.display = 'none';
            }
        }

        // Initial state
        toggleOrdinalFields();

        // Listen for changes
        frequencyField.addEventListener('change', toggleOrdinalFields);
    }
});