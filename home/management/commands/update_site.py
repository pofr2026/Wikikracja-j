"""
Django management command to sync Site domain and name from environment variables.

Purpose:
    Updates the django_site table (Site model) with values from SITE_DOMAIN and SITE_NAME
    environment variables. This ensures the Site object matches the current deployment
    configuration without requiring database migrations.

Why this exists:
    The post_migrate signal in home/apps.py only fires when migrations actually run.
    On container restart, if there are no new migrations, the signal doesn't fire and
    the Site record can become stale or remain at default (example.com).

When it runs:
    Automatically on every container startup (see Dockerfile CMD).
    Can also be run manually: python manage.py update_site
"""
# Standard library imports
import os

# Third party imports
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Update Site domain and name from environment variables'

    def handle(self, *args, **options):
        site_domain = os.getenv('SITE_DOMAIN')
        site_name = os.getenv('SITE_NAME')

        if not site_domain:
            self.stdout.write(self.style.WARNING('SITE_DOMAIN not set in environment'))
            return

        try:
            site = Site.objects.get(id=1)
            updated = False

            if site.domain != site_domain:
                site.domain = site_domain
                updated = True

            if site_name and site.name != site_name:
                site.name = site_name
                updated = True

            if updated:
                site.save()
                self.stdout.write(self.style.SUCCESS(f'Updated Site: {site.domain} - {site.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Site already up to date: {site.domain} - {site.name}'))

        except Site.DoesNotExist:
            site = Site.objects.create(id=1, domain=site_domain, name=site_name or site_domain)
            self.stdout.write(self.style.SUCCESS(f'Created Site: {site.domain} - {site.name}'))
