# Standard library imports
import logging
import time
from collections import defaultdict
from datetime import timedelta as td
from random import choice
from string import ascii_letters, digits

# Third party imports
from django.conf import settings as s
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.db.models import Sum
from django.utils.timezone import now
from django.utils.translation import gettext as _

# First party imports
from chat import signals
from chat.models import Room
from obywatele.models import CitizenActivity, Rate, Uzytkownik
from obywatele.signals import track_user_blocked
from obywatele.views import SendEmailToAll, required_reputation
from zzz.utils import get_site_domain

log = logging.getLogger(__name__)


def password_generator(size=8, chars=ascii_letters + digits):
    return ''.join(choice(chars) for i in range(size))


# count_citizens command
class Command(BaseCommand):
    help = 'Count citizens\' reputation and activate/deactivate users based on reputation thresholds'

    def handle(self, *args, **options):
        ts = now().strftime('%Y-%m-%d %H:%M:%S%z')
        self.stdout.write(f'[{ts}] Starting citizen count and reputation check...')

        # Clean up duplicate users FIRST
        self.cleanup_duplicate_users()

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

        ts = now().strftime('%Y-%m-%d %H:%M:%S%z')
        self.stdout.write(self.style.SUCCESS(f'[{ts}] Successfully processed citizens'))

    def cleanup_duplicate_users(self):
        """Remove duplicate users with the same email before processing"""
        # Find all users grouped by email (case-insensitive)
        email_to_users = defaultdict(list)
        for user in User.objects.all():
            email_to_users[user.email.lower()].append(user)

        # Process duplicates
        for email, users in email_to_users.items():
            if len(users) > 1:
                log.warning(f'Found {len(users)} users with email {email}')

                # Sort: active first, then by date_joined (newest first)
                users.sort(key=lambda u: (not u.is_active, -u.date_joined.timestamp()))

                # Keep the first one (active and newest)
                user_to_keep = users[0]
                users_to_delete = users[1:]

                log.info(f'Keeping user {user_to_keep.username} (id={user_to_keep.id}, active={user_to_keep.is_active})')

                for user in users_to_delete:
                    log.info(f'Deleting duplicate user {user.username} (id={user.id}, active={user.is_active})')

                    # Delete associated profile if exists
                    try:
                        if hasattr(user, 'uzytkownik'):
                            user.uzytkownik.delete()
                    except Exception as e:
                        log.error(f'Error deleting profile for user {user.id}: {e}')

                    # Delete the user
                    try:
                        user.delete()
                    except Exception as e:
                        log.error(f'Error deleting user {user.id}: {e}')

    def count_reputation(self):
        """Count everyone's reputation from Rate model and update the Uzytkownik model"""
        for i in Uzytkownik.objects.all():
            if i.uid_id is None or not User.objects.filter(pk=i.uid_id).exists():
                log.warning(f"Deleting orphaned Uzytkownik profile id={i.id} (uid_id={i.uid_id})")
                i.delete()
                continue

            if Rate.objects.filter(kandydat=i).exists():
                reputation = Rate.objects.filter(kandydat=i).aggregate(Sum('rate'))
                i.reputation = list(reputation.values())[0]
            else:
                i.reputation = 0

            try:
                i.save()
            except IntegrityError as e:
                log.error(f"Skipping reputation update for profile id={i.id}, uid_id={i.uid_id}: {e}")

    def activate_eligible_users(self):
        """Activate users with sufficient reputation"""

        inactive_users = list(Uzytkownik.objects.filter(uid__is_active=False))
        req_rep = required_reputation()

        for i in inactive_users:
            # CRITICAL: Skip if uid is None or invalid
            if i.uid is None or i.uid_id is None or i.uid_id <= 0:
                log.warning(f'Skipping Uzytkownik id={i.id} with invalid uid_id={i.uid_id}')
                continue

            if i.reputation is None:
                log.warning(f'User {i.uid.username} has None reputation, skipping activation')
                continue

            if i.reputation > req_rep:
                log.info(f'EMAIL_DIAG trigger=count_citizens_activation_check user_id={i.uid.id} email={i.uid.email} username={i.uid.username} reputation={i.reputation} required_reputation={req_rep}')
                # Generate password first
                password = password_generator()

                # Atomically activate user only if still inactive (prevents race condition)
                # This returns number of rows updated - will be 0 if user already active
                rows_updated = User.objects.filter(id=i.uid.id, is_active=False).update(is_active=True, password=make_password(password))

                # If no rows updated, user was already activated by another process
                if rows_updated == 0:
                    log.info(f'User {i.uid.username} (id={i.uid.id}) already activated by another process, skipping')
                    continue

                # User was successfully activated by THIS process
                log.info(f'ACTIVATING: user_id={i.uid.id}, email={i.uid.email}, username={i.uid.username}, uzytkownik_id={i.id}')
                i.data_przyjecia = now()
                i.save()

                CitizenActivity.objects.create(
                    uzytkownik=i,
                    activity_type=CitizenActivity.ActivityType.USER_ACTIVATED,
                    description=_('Candidate has been accepted as a citizen')
                )

                # Log the generated password for debugging
                log.info(f'Generated password for {i.uid.email}: {password}')
                log.info(f'ACTIVATED: user_id={i.uid.id}, email={i.uid.email}')

                # Create one2one chat rooms for new person with Signals
                log.info(f'EMAIL_DIAG trigger=user_accepted_signal user_id={i.uid.id} email={i.uid.email} username={i.uid.username} source=count_citizens.activate_eligible_users')
                signals.user_accepted.send(sender='user_accepted', user=i)

                # New person accepts automatically every other active user
                for k in Uzytkownik.objects.filter(uid__is_active=True):
                    if i == k:  # but not yourself
                        continue
                    obj, created = Rate.objects.update_or_create(obywatel=i, kandydat=k, defaults={
                        'rate': '1'
                    })
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
{_('Password')}: {password}\n\n\
{_('You may login here')}: {host}/login/\n\n\
{_('You may change password here')}: {host}/haslo/\
"""
                try:
                    log.info(f'EMAIL_DIAG trigger=welcome_email user_id={i.uid.id} email={uemail} username={uname} source=count_citizens.activate_eligible_users subject={subject}')
                    time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
                    send_mail(subject, message, s.DEFAULT_FROM_EMAIL, [uemail], fail_silently=False)
                    log.info(f'Sent welcome email to {uemail}')
                except Exception as e:
                    log.error(f'Failed to send welcome email to {uemail}: {str(e)}')

    def block_ineligible_users(self):
        """Block users with insufficient reputation"""
        req_rep = required_reputation()
        for i in Uzytkownik.objects.filter(uid__is_active=True):
            if i.reputation < req_rep:
                i.uid.is_active = False
                i.uid.save()
                i.save()
                log.info(f'Blocking user {i.uid}')
                
                # Track the blocking activity only if user was previously active
                track_user_blocked(i, was_previously_active=True)

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
                    log.info(f'Sent account blocked notification to {i.uid.email}')
                except Exception as e:
                    log.error(f'Failed to send account blocked notification to {i.uid.email}: {str(e)}')

                SendEmailToAll(_('Citizen has been banned'), f"{_('User')} {uname} {_('has been blocked')}")

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
                    log.info(f'Deleted inactive user: {user.username}')
                except Exception as e:
                    log.error(f'Failed to delete user {user.id}: {str(e)}')
