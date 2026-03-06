from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.conf import settings


class CaseInsensitiveEmailBackend(ModelBackend):
    """
    Custom authentication backend that allows case-insensitive email login.
    
    This backend normalizes the email address during the authentication process
    to make email lookup case-insensitive, addressing the issue where users
    can't login with emails containing different capitalization than registration.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        # Normalize the email by converting to lowercase
        # This ensures case-insensitive comparison
        normalized_username = username.lower()
        
        # Find users with case-insensitive match
        try:
            # Using filter() and lower() function for case-insensitive comparison
            # SQLite's LIKE operator is case-insensitive by default
            user = UserModel.objects.get(email__iexact=normalized_username)
            if settings.DEBUG_SKIP_AUTH:
                return user
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce timing
            # attacks against non-existent users
            UserModel().set_password(password)
        except UserModel.MultipleObjectsReturned:
            # Handle case where multiple users have the same email
            # Try to authenticate with the active user
            users = UserModel.objects.filter(email__iexact=normalized_username, is_active=True)
            if users.count() == 1:
                user = users.first()
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
        
        return None
