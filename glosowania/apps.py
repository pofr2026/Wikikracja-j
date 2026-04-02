# Third party imports
from django.apps import AppConfig


class VotingConfig(AppConfig):
    name = 'glosowania'

    def ready(self):
        import glosowania.signals  # noqa
