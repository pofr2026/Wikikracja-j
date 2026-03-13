"""
Tests for email deduplication:
  1. New person sign-up → SendEmailToAll fires exactly once.
  2. chat_messages command → each user receives exactly one email per run.

Settings are loaded from .env (via zzz/settings.py as usual).
EMAIL_SEND_DELAY_SECONDS is overridden to 0 so threads finish quickly.
EMAIL_BACKEND is overridden to locmem so no real SMTP is used.
"""
import threading
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytz
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.timezone import make_aware

from chat.models import Room, Message
from obywatele.models import Uzytkownik


FAST_EMAIL_SETTINGS = {
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'EMAIL_SEND_DELAY_SECONDS': 0,
}


def _drain_threads():
    """Wait for all non-main daemon threads to finish (email background threads)."""
    main = threading.main_thread()
    for t in threading.enumerate():
        if t is main or not t.daemon:
            continue
        t.join(timeout=5)


# ---------------------------------------------------------------------------
# Helper: create an active user + Uzytkownik profile
# ---------------------------------------------------------------------------
def make_active_user(username, email):
    user = User.objects.create_user(username=username, email=email, password='pass')
    user.is_active = True
    user.save()
    # Uzytkownik is auto-created via post_save signal
    return user


# ---------------------------------------------------------------------------
# 1. New person sign-up email
# ---------------------------------------------------------------------------
@override_settings(**FAST_EMAIL_SETTINGS)
class NewPersonEmailTest(TestCase):
    """SendEmailToAll is called exactly once when a new person signs up."""

    def _call_send_email_to_all(self, subject, message):
        from obywatele.forms import SendEmailToAll
        SendEmailToAll(subject, message)
        _drain_threads()

    def test_send_email_to_all_sends_exactly_one_email(self):
        """A single SendEmailToAll call results in exactly one sent email."""
        make_active_user('citizen1', 'citizen1@example.com')
        make_active_user('citizen2', 'citizen2@example.com')

        self._call_send_email_to_all('Test subject', 'Test message')

        self.assertEqual(len(mail.outbox), 1, (
            f"Expected 1 email, got {len(mail.outbox)}. "
            "Double-sending would produce 2 or more emails."
        ))

    def test_send_email_to_all_sends_exactly_one_email_on_repeated_calls(self):
        """Two separate events each produce exactly one email (not doubled)."""
        make_active_user('citizen3', 'citizen3@example.com')

        self._call_send_email_to_all('First event', 'First message')
        self._call_send_email_to_all('Second event', 'Second message')

        self.assertEqual(len(mail.outbox), 2, (
            f"Expected 2 emails (one per event), got {len(mail.outbox)}."
        ))

    def test_send_email_to_all_from_forms_not_views_is_same_function(self):
        """forms.py and views.py define separate SendEmailToAll functions.
        Both should produce exactly one email per call."""
        from obywatele.forms import SendEmailToAll as forms_send
        from obywatele.views import SendEmailToAll as views_send

        make_active_user('citizen4', 'citizen4@example.com')

        forms_send('Forms subject', 'Forms message')
        _drain_threads()

        views_send('Views subject', 'Views message')
        _drain_threads()

        self.assertEqual(len(mail.outbox), 2, (
            f"Expected 2 emails (one from forms, one from views), got {len(mail.outbox)}."
        ))

    def test_no_email_when_no_active_users(self):
        """No email is sent when there are no active users."""
        self._call_send_email_to_all('Empty subject', 'Empty message')
        # One email sent with empty BCC list (Django still sends it to from_email)
        # OR zero emails - both are acceptable; what matters is not 2+
        self.assertLessEqual(len(mail.outbox), 1, (
            f"Expected at most 1 email with no active users, got {len(mail.outbox)}."
        ))


# ---------------------------------------------------------------------------
# 2. Chat messages email
# ---------------------------------------------------------------------------
@override_settings(**FAST_EMAIL_SETTINGS)
class ChatMessagesEmailTest(TestCase):
    """chat_messages Command sends exactly one email per user per run."""

    def _run_chat_messages_command(self):
        from django.core.management import call_command
        call_command('chat_messages')
        _drain_threads()

    def setUp(self):
        self.sender = make_active_user('sender', 'sender@example.com')
        self.recipient = make_active_user('recipient', 'recipient@example.com')

        # Create a public room with both users allowed
        self.room = Room.objects.create(title='Test Room', public=True)
        self.room.allowed.set([self.sender, self.recipient])

        # Set last_broadcast far in the past so new messages are detected
        past = make_aware(datetime(1900, 1, 1))
        Uzytkownik.objects.filter(uid=self.recipient).update(last_broadcast=past)
        Uzytkownik.objects.filter(uid=self.sender).update(last_broadcast=past)

    def _add_message(self, text='Hello'):
        return Message.objects.create(
            sender=self.sender,
            room=self.room,
            text=text,
        )

    def test_one_email_per_user_with_new_messages(self):
        """Recipient receives exactly one email when there are new messages."""
        self._add_message('Hello there')

        self._run_chat_messages_command()

        # Only recipient gets an email (sender is excluded from their own messages)
        recipient_emails = [e for e in mail.outbox if self.recipient.email in e.bcc]
        self.assertEqual(len(recipient_emails), 1, (
            f"Expected 1 email for recipient, got {len(recipient_emails)}. "
            "Double-sending would show 2."
        ))

    def test_no_email_when_no_new_messages(self):
        """No email is sent when there are no messages since last_broadcast."""
        # Set last_broadcast to future so no messages qualify
        from django.utils.timezone import now
        future = now()
        Uzytkownik.objects.filter(uid=self.recipient).update(last_broadcast=future)

        self._run_chat_messages_command()

        recipient_emails = [e for e in mail.outbox if self.recipient.email in e.bcc]
        self.assertEqual(len(recipient_emails), 0, (
            f"Expected 0 emails when no new messages, got {len(recipient_emails)}."
        ))

    def test_one_email_aggregates_multiple_messages(self):
        """Multiple new messages in one room → still only one email per user."""
        self._add_message('Message 1')
        self._add_message('Message 2')
        self._add_message('Message 3')

        self._run_chat_messages_command()

        recipient_emails = [e for e in mail.outbox if self.recipient.email in e.bcc]
        self.assertEqual(len(recipient_emails), 1, (
            f"Expected 1 aggregated email, got {len(recipient_emails)}."
        ))

    def test_running_command_twice_sends_two_emails(self):
        """Two separate runs (different broadcast windows) each send one email."""
        self._add_message('First batch')
        self._run_chat_messages_command()

        # Add a new message AFTER last_broadcast was updated by first run
        # Simulate by resetting last_broadcast
        past = make_aware(datetime(1900, 1, 1))
        Uzytkownik.objects.filter(uid=self.recipient).update(last_broadcast=past)
        self._add_message('Second batch')
        self._run_chat_messages_command()

        recipient_emails = [e for e in mail.outbox if self.recipient.email in e.bcc]
        self.assertEqual(len(recipient_emails), 2, (
            f"Expected 2 emails (one per run), got {len(recipient_emails)}."
        ))

    def test_muted_room_no_email(self):
        """User who muted a room does not receive email notifications for it."""
        self.room.muted_by.add(self.recipient)
        self._add_message('Should not be notified')

        self._run_chat_messages_command()

        recipient_emails = [e for e in mail.outbox if self.recipient.email in e.bcc]
        self.assertEqual(len(recipient_emails), 0, (
            f"Expected 0 emails for muted room, got {len(recipient_emails)}."
        ))

    def test_sender_does_not_receive_own_message_email(self):
        """The message sender does not receive an email about their own message."""
        self._add_message('My own message')

        self._run_chat_messages_command()

        sender_emails = [e for e in mail.outbox if self.sender.email in e.bcc]
        self.assertEqual(len(sender_emails), 0, (
            f"Sender should not receive email for own message, got {len(sender_emails)}."
        ))
