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
	
	toggles.forEach(toggle => {
		toggle.addEventListener('change', function() {
			const type = this.dataset.url.split('type=')[1];
			const statusBadge = document.getElementById('status-' + type);
			const isChecked = this.checked;
			
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
