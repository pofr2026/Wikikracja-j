# Standard library imports
import logging

# Third party imports
from django.conf import settings
from django.http import HttpRequest

# First party imports
from board.models import Post
import subprocess
import os
from datetime import datetime

log = logging.getLogger(__name__)


def footer(request: HttpRequest):
    footer = Post.objects.filter(title__iexact='Footer').order_by('-updated').first()
    return {
        'footer': footer
    }


def site_description(request):
    return {
        'site_description': settings.SITE_DESCRIPTION
    }


def vapid_public_key(request):
    return {
        'vapid_public_key': settings.PUSH_NOTIFICATIONS['WEBPUSH'].get('VAPID_PUBLIC_KEY', '')
    }


    # Firebase configuration from settings
    # firebase_config = {
    #     'apiKey': s.PUSH_NOTIFICATIONS.get('FCM', {}).get('API_KEY', ''),
    #     'authDomain': '',  # Will be constructed from project ID
    #     'projectId': s.PUSH_NOTIFICATIONS.get('FCM', {}).get('PROJECT_ID', ''),
    #     'storageBucket': '',  # Will be constructed from project ID
    #     'messagingSenderId': s.PUSH_NOTIFICATIONS.get('FCM', {}).get('SERVER_KEY', '').split(':')[0] if s.PUSH_NOTIFICATIONS.get('FCM', {}).get('SERVER_KEY') else '',
    #     'appId': s.PUSH_NOTIFICATIONS.get('FCM', {}).get('APP_ID', '')
    # }

    # # Construct authDomain and storageBucket if project ID is available
    # if firebase_config['projectId']:
    #     firebase_config['authDomain'] = f"{firebase_config['projectId']}.firebaseapp.com"
    #     firebase_config['storageBucket'] = f"{firebase_config['projectId']}.appspot.com"
