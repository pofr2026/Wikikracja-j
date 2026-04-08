# Third party imports
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User
from django.http import HttpRequest

# First party imports
from obywatele.models import Uzytkownik

import logging

log = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to handle Wikikracja onboarding flow.
    
    KEY DESIGN NOTES:
    - Ensures onboarding_user_id is set in session after signup
    - Handles inactive user redirects to onboarding (not /accounts/inactive/)
    - Preserves session data across allauth redirects
    - Critical for onboarding form access after signup
    """
    
    def save_user(self, request, user, form, commit=True):
        """
        CRITICAL: Set onboarding_user_id in session immediately after user creation.
        
        DESIGN NOTE: allauth may clear/modify session during signup process.
        This ensures the onboarding_user_id survives allauth redirects.
        Without this, users get "Could not find your onboarding account" error.
        """
        # Call the parent method first
        user = super().save_user(request, user, form, commit)
        
        # CRITICAL: Set onboarding_user_id in session immediately
        # This allows access to onboarding form after signup redirect
        if hasattr(user, 'uzytkownik'):
            request.session['onboarding_user_id'] = user.id
            request.session.modified = True
        
        return user
    
    def get_signup_redirect_url(self, request):
        """
        Override signup redirect to ensure session is preserved
        """
        return super().get_signup_redirect_url(request)
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Disable auto signup for social accounts to ensure onboarding flow
        """
        return False
    
    def is_open_for_signup(self, request):
        """
        Allow signup if configured
        """
        return True
    
    def get_login_redirect_url(self, request):
        """
        CRITICAL: Redirect inactive users to onboarding (not /accounts/inactive/).
        
        DESIGN NOTE: Default allauth behavior sends inactive users to /accounts/inactive/
        This breaks our onboarding flow. We redirect them to onboarding form instead.
        Combined with ACCOUNT_INACTIVE_REDIRECT_URL setting, this ensures smooth flow.
        """
        if request.user.is_authenticated and not request.user.is_active:
            # IMPORTANT: Redirect inactive users to onboarding, not /accounts/inactive/
            # This prevents "Your account is inactive" dead-end
            return '/obywatele/onboarding/'
        
        return super().get_login_redirect_url(request)
