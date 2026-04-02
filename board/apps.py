# Third party imports
from django.apps import AppConfig


class BoardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'board'

    def ready(self):
        # Import signals to register them
        # First party imports
        import board.signals  # noqa: F401
