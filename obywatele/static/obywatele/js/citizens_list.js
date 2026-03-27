/**
 * @file
 * Citizens list page interactive functionality.
 * Handles clickable table rows for viewing user details and copy email buttons.
 */

/**
 * Initializes interactive features on the citizens list page
 * Sets up event listeners when DOM is fully loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    /**
     * Makes table rows clickable to view user details
     * Ignores clicks on interactive elements like buttons and links
     */
    const rows = document.querySelectorAll('.user-row');
    rows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Only navigate if the click wasn't on a button or other interactive element
            if (!e.target.closest('button, a')) {
                const userId = this.getAttribute('data-user-id');
                window.location.href = `/obywatele/poczekalnia/${userId}/`;
            }
        });
    });
    
    /**
     * Copy email buttons functionality
     * Copies email to clipboard and shows visual feedback
     */
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent row click
            const email = this.getAttribute('data-email');
            navigator.clipboard.writeText(email)
                .then(() => {
                    // Visual feedback - show success state
                    const originalHTML = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i>';
                    this.classList.remove('btn-light');
                    this.classList.add('btn-success');
                    
                    // Restore original state after 1.5 seconds
                    setTimeout(() => {
                        this.innerHTML = originalHTML;
                        this.classList.remove('btn-success');
                        this.classList.add('btn-light');
                    }, 1500);
                })
                .catch(err => {
                    console.error('Failed to copy email:', err);
                });
        });
    });
});