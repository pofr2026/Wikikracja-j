// Profile page - email notification toggles

document.addEventListener('DOMContentLoaded', function() {
	const toggles = document.querySelectorAll('[id^="toggle-"]');
	
	function updateBadge(badge, isEnabled) {
		badge.className = isEnabled ? 'badge bg-success' : 'badge bg-secondary';
		badge.textContent = isEnabled ? badge.dataset.enabledText : badge.dataset.disabledText;
	}
	
	function handleError(toggle, badge, wasChecked) {
		toggle.checked = !wasChecked;
		badge.className = 'badge bg-danger';
		badge.textContent = badge.dataset.errorText;
		setTimeout(() => updateBadge(badge, !wasChecked), 2000);
	}
	
	function getCookie(name) {
		const value = `; ${document.cookie}`;
		const parts = value.split(`; ${name}=`);
		if (parts.length === 2) return parts.pop().split(';').shift();
	}
	
	const MUTUALLY_EXCLUSIVE = [['toggle-chat', 'toggle-chat_participated']];

	function disableToggle(toggleId) {
		const toggle = document.getElementById(toggleId);
		if (!toggle || !toggle.checked) return;
		toggle.checked = false;
		const type = toggle.dataset.url.split('type=')[1];
		const badge = document.getElementById('status-' + type);
		fetch(toggle.dataset.url, {
			method: 'POST',
			headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
			body: JSON.stringify({ enabled: false })
		}).then(r => r.json()).then(data => { if (data.success) updateBadge(badge, false); });
	}

	toggles.forEach(toggle => {
		toggle.addEventListener('change', function() {
			const type = this.dataset.url.split('type=')[1];
			const statusBadge = document.getElementById('status-' + type);
			const isChecked = this.checked;

			// Mutual exclusion
			if (isChecked) {
				MUTUALLY_EXCLUSIVE.forEach(group => {
					if (group.includes(this.id)) {
						group.filter(id => id !== this.id).forEach(disableToggle);
					}
				});
			}
			
			statusBadge.className = 'badge bg-warning';
			statusBadge.textContent = statusBadge.dataset.savingText;
			
			fetch(this.dataset.url, {
				method: 'POST',
				headers: {
					'X-CSRFToken': getCookie('csrftoken'),
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ enabled: isChecked })
			})
			.then(response => response.json())
			.then(data => {
				if (data.success) {
					updateBadge(statusBadge, isChecked);
				} else {
					handleError(this, statusBadge, isChecked);
				}
			})
			.catch(() => handleError(this, statusBadge, isChecked));
		});
	});
});
