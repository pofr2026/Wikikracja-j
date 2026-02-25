import logging
import pytz
import threading

from datetime import datetime as dt
from time import sleep
from django.utils import timezone, translation
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.conf import settings as s
from chat.models import Room, Message
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from obywatele.models import Uzytkownik
from zzz.utils import get_site_domain

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = ''
    help = 'Send chat messages through email'

    def handle(self, *args, **options):
        pass
        '''Jeśli tego nie będzie to: raise NotImplementedError('subclasses of BaseCommand must provide a handle() method')
        NotImplementedError: subclasses of BaseCommand must provide a handle() method'''

    def __init__(self, *args, **kwargs):
        translation.activate(s.LANGUAGE_CODE)

        # Configure the root logger (this approach is used by the original code)
        logging.basicConfig(filename='/var/log/wiki.log', datefmt='%d-%b-%y %H:%M:%S', 
                          format='%(asctime)s %(levelname)s %(funcName)s() %(message)s', 
                          level=logging.INFO)
    
        HOST = get_site_domain()
    
        def SendEmail(recipients: list[str], message: str) -> None:
            
            subject = _("{HOST} New messages on chat").format(HOST=HOST)
            header = _("New messages on {HOST}/chat").format(HOST=HOST)
            footer1 = _("You can disable those messages by unchecking bell icon next to chat room name.")
            footer2 = _("Go to chat to do so {HOST}/chat").format(HOST=HOST)

            email_message = EmailMessage(
                subject = subject,
                body = header + "\n\n" + message + "\n\n" + footer1 + "\n" + footer2,
                from_email = str(s.DEFAULT_FROM_EMAIL),
                bcc = recipients,
                )
            log.info(f'SENDING - Subject: {email_message.subject}; TO: {email_message.bcc};')

            def _send_with_delay():
                sleep(s.EMAIL_SEND_DELAY_SECONDS)
                email_message.send(fail_silently=False)

            t = threading.Thread(target=_send_with_delay)
            t.setDaemon(True)
            t.start()

        user_list = Uzytkownik.objects.filter(uid__is_active=True)
        for u in user_list:
            room_allowed = Room.objects.filter(allowed=u.uid, archived=False).exclude(muted_by=u.uid, seen_by=u.uid)
            message_list = Message.objects.filter(time__gte=u.last_broadcast, room__in=room_allowed).exclude(sender=u.uid)
            if not message_list:
                log.info(f'No new messages for user {u.uid}')
                continue

            # Group messages by room
            from collections import defaultdict
            messages_by_room = defaultdict(list)
            for m in message_list.order_by('room', 'time'):
                messages_by_room[m.room].append(m)

            b: list[str] = []
            for room, messages in messages_by_room.items():
                # Add room header with name as link
                room_link = f"{HOST}/chat#room_id={room.id}"
                room_name = room.displayed_name(u.uid)
                b.append(f"## {room_name}: {room_link}")
                b.append("")
                
                # Add messages without date/time/room
                for m in messages:
                    log.info(f'Found messages for user {u.uid}: {m.text}')
                    if m.anonymous:
                        m.sender = None
                    b.append(f'{m.sender}: {m.text}')
                
                b.append("")  # Empty line between rooms

            body = "\n".join(b)
            if body:
                SendEmail([u.uid.email,], body)
            u.last_broadcast = dt.now(pytz.timezone('Europe/Warsaw')) # TODO: Wziąć to z settings.py
            u.save()
