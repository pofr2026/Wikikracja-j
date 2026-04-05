# Third party imports
from django.apps import AppConfig


class ObywateleConfig(AppConfig):
    name = 'obywatele'
    
    def ready(self):
        import obywatele.signals
