from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings as s
from django.core.mail import send_mail
from django.utils.timezone import now
from django.utils.translation import gettext as _
import pytz
from datetime import timedelta as td
from datetime import datetime
from obywatele.models import Uzytkownik, Rate
from obywatele.views import required_reputation, password_generator, SendEmailToAll
from django.db.models import Sum
from chat import signals
from zzz.utils import get_site_domain
import time

import logging
log = logging.getLogger('django')

class Command(BaseCommand):
    help = 'Count citizens\' reputation and activate/deactivate users based on reputation thresholds'

    def handle(self, *args, **options):
        self.stdout.write('Starting citizen count and reputation check...')
        
        # Count reputation for all users
        self.count_reputation()
        
        # Activate users with sufficient reputation
        self.activate_eligible_users()
        
        # Count reputation again after activations
        self.count_reputation()
        
        # Block users with insufficient reputation
        self.block_ineligible_users()
        
        # Delete inactive users after grace period
        self.delete_inactive_users()
        
        self.stdout.write(self.style.SUCCESS('Successfully processed citizens'))

    def count_reputation(self):
        """Count everyone's reputation from Rate model and update the Uzytkownik model"""
        for i in Uzytkownik.objects.all():
            if Rate.objects.filter(kandydat=i).exists():
                reputation = Rate.objects.filter(kandydat=i).aggregate(Sum('rate'))
                i.reputation = list(reputation.values())[0]
                i.save()
    
    def activate_eligible_users(self):
        """Activate users with sufficient reputation"""
        for i in Uzytkownik.objects.filter(uid__is_active=False):
            if i.reputation > required_reputation():
                i.uid.is_active = True  # Uzytkownik.uid -> User
                
                password = password_generator()
                i.uid.set_password(password)
                i.data_przyjecia = now()
                i.uid.save()
                i.save()
                log.info(f'Activating user {i.uid}')

                # Create one2one chat rooms for new person with Signals
                signals.user_accepted.send(sender='user_accepted', user=i)
                
                # New person accepts automatically every other active user
                for k in Uzytkownik.objects.filter(uid__is_active=True):
                    if i == k:    # but not yourself
                        continue
                    obj, created = Rate.objects.update_or_create(obywatel=i, kandydat=k, defaults={'rate': '1'})
                    obj.save()

                uname = str(i.uid.username)
                uemail = str(i.uid.email)
                
                # Get the domain from django_site table
                host = get_site_domain()
                
                subject = '[' + host + '] ' + _('You have been accepted in our community')
                message = f"""\
{_('Welcome')} {uname} \n\
{_('Your account on')} {host} {_('is now active')} \n\n\
{_('Login')}: {uemail} \n\
{_('Password')}: {password} \n\n\
{_('You may login here')}: {host}/login/\n\n\
{_('You may change password here')}: {host}/haslo/\
"""
                try:
                    time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
                    send_mail(subject, message, s.DEFAULT_FROM_EMAIL, [uemail], fail_silently=False)
                    self.stdout.write(f'Sent welcome email to {uemail}')
                except Exception as e:
                    self.stderr.write(f'Failed to send welcome email to {uemail}: {str(e)}')
    
    def block_ineligible_users(self):
        """Block users with insufficient reputation"""
        for i in Uzytkownik.objects.filter(uid__is_active=True):
            if i.reputation < required_reputation():
                i.uid.is_active = False
                i.uid.save()
                i.save()
                log.info(f'Blocking user {i.uid}')

                # Banned person resets other people's reputation to Neutral
                Rate.objects.filter(obywatel=i.id).update(rate=0)

                host = get_site_domain()
                
                uname = str(i.uid.username)
                sender = str(s.DEFAULT_FROM_EMAIL)
                bcc = [i.uid.email]

                subject = '[' + host + '] ' + _('Your account has been blocked')
                message = f"""\
{_('Welcome')} {uname} \n\
{_('Your account on')} {host} {_('has been blocked')}\n\n\
"""
                try:
                    time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
                    send_mail(subject, message, sender, bcc, fail_silently=False)
                    self.stdout.write(f'Sent account blocked notification to {i.uid.email}')
                except Exception as e:
                    self.stderr.write(f'Failed to send account blocked notification to {i.uid.email}: {str(e)}')

                SendEmailToAll(
                    _('Citizen has been banned'),
                    f"{_('User')} {uname} {_('has been blocked')}"
                )
    
    def delete_inactive_users(self):
        """Delete inactive users who haven't logged in for a while"""
        inactive_period = s.DELETE_INACTIVE_USER_AFTER if hasattr(s, 'DELETE_INACTIVE_USER_AFTER') else 30
        
        for user in User.objects.filter(is_active=False):
            if user.last_login is None:
                user.last_login = now()  # Set to current date
                user.save()
            
            if user.last_login < (now() - td(days=inactive_period)):
                signals.user_deleted.send(sender='user_deleted', user=user)
                try:
                    if hasattr(user, 'uzytkownik'):
                        user.uzytkownik.delete()
                    
                    # Remove user from all rooms' allowed/muted/seen_by
                    from chat.models import Room
                    for room in Room.objects.filter(allowed=user):
                        room.allowed.remove(user)
                    for room in Room.objects.filter(muted_by=user):
                        room.muted_by.remove(user)
                    for room in Room.objects.filter(seen_by=user):
                        room.seen_by.remove(user)
                    
                    # Remove from groups and permissions
                    user.groups.clear()
                    user.user_permissions.clear()
                    
                    # Finally delete the user
                    user.delete()
                    self.stdout.write(f'Deleted inactive user: {user.username}')
                except Exception as e:
                    self.stderr.write(f'Failed to delete user {user.id}: {str(e)}')
