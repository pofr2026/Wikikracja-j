# Standard library imports
import os

# Third party imports
from django.apps import AppConfig
from django.contrib.sites.models import Site
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class HomeConfig(AppConfig):
    name = 'home'

    def ready(self):
        @receiver(post_migrate)
        def update_site_domain(sender, **kwargs):
            """Update Site domain from environment variables after migrations."""

            site_domain = os.getenv('SITE_DOMAIN')
            site_name = os.getenv('SITE_NAME')

            if site_domain:
                try:
                    site = Site.objects.get(id=1)
                    if site.domain != site_domain or (site_name and site.name != site_name):
                        site.domain = site_domain
                        if site_name:
                            site.name = site_name
                        site.save()
                except Site.DoesNotExist:
                    Site.objects.create(id=1, domain=site_domain, name=site_name or site_domain)
                except Exception:
                    pass
