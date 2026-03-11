from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from glosowania.models import Decyzja
from chat.models import Room, Message
import logging
from zzz.utils import get_site_domain

log = logging.getLogger(__name__)


@receiver(post_save, sender=Decyzja)
def create_chat_room_for_referendum(sender, instance, created, **kwargs):
    """
    Create a public chat room for each new project (Decyzja) when it is created.
    """
    # Only create room when a new Decyzja is created (status 1 = Proposition)
    if created and instance.status == 1:
        # Create room title based on project ID and title
        room_title = _("Vote #%(id)s: %(title)s") % {"id": instance.pk, "title": instance.title[:20]}
        
        # Check if room already exists (safety check)
        existing_room = Room.objects.filter(title=room_title).first()
        
        if not existing_room:
            try:
                # Create new public chat room
                room = Room.objects.create(
                    title=room_title,
                    public=True,
                    archived=False
                )
                
                # Add all active users to the room
                active_users = User.objects.filter(is_active=True)
                room.allowed.set(active_users)
                
                # Create initial welcome message in the room
                HOST = get_site_domain()
                details_url = f"http://{HOST}/glosowania/details/{instance.pk}"
                welcome_message = _(
                    "This chat room has been created for project #{id}.\n"
                    "View details: {details_url}\n"
                    "Discuss the proposal, share your thoughts, and ask questions here."
                ).format(id=instance.pk, details_url=details_url)
                
                Message.objects.create(
                    room=room,
                    text=welcome_message,
                    anonymous=True,
                    sender=None
                )
                
                log.info(f'Chat room "{room_title}" created for referendum #{instance.pk}')
            except Exception as e:
                log.error(f'Failed to create chat room for referendum #{instance.pk}: {str(e)}')
