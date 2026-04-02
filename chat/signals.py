# Third party imports
from django.dispatch import Signal

# Sends signal to @receiver(user_accepted) in views
user_accepted = Signal()

# Sends signal to @receiver(user_deleted) in views
user_deleted = Signal()
