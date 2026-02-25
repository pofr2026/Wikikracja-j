import imghdr
import json
import logging
import uuid

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from .models import Room, Message
from django.contrib.auth.models import User
from chat.forms import RoomForm
from django.http import HttpRequest, JsonResponse
from datetime import timedelta as td
from django.utils import timezone
from django.shortcuts import redirect
from django.conf import settings as s
from django.dispatch import receiver
from chat.signals import user_accepted, user_deleted
from django.utils.translation import gettext_lazy as _
from chat.models import Room

log = logging.getLogger(__name__)

@login_required
def add_room(request: HttpRequest):
    """
    Add public chat room
    """
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.last_activity = timezone.now()
            room.save()

            # Allow active user access to new public rooms
            active_users = User.objects.filter(is_active=True)
            public_rooms = Room.objects.filter(public=True)
            for i in public_rooms:
                i.allowed.set(active_users)

            return redirect(f"{reverse('chat:chat')}#room_id={room.id}")
    else:
        form = RoomForm()
    return render(request, 'chat/add.html', {'form': form})


@login_required
def chat(request: HttpRequest):
    """
    Root page view. This is essentially a single-page app, if you ignore the
    login and admin parts.
    """
    # TODO: This can be optimized with Signals or CRON

    # Allow active user access to all public rooms
    public_rooms = Room.objects.filter(public=True)
    private_rooms = Room.objects.filter(public=False)
    active_users = User.objects.filter(is_active=True)

    for p in public_rooms:
        p.allowed.set(active_users)
    
    # create_one2one_rooms(user_accepted)  # use it if there is no private rooms

    # Archive/Delete old public chat rooms
    for room in public_rooms:
        try:
            last_message = Message.objects.filter(room_id=room.id).latest('time')
        except Message.DoesNotExist:
            # logger.info(f'Message.DoesNotExist1 in {room}')
            continue
        if last_message.time < (timezone.now() - td(days=s.ARCHIVE_PUBLIC_CHAT_ROOM)):  # archive public after 3 months
            log.info(f'Chat room {room.title} archived.')
            room.archived = True  # archive
            room.save()
        elif last_message.time > (timezone.now() - td(days=s.ARCHIVE_PUBLIC_CHAT_ROOM)):  # unarchive
            room.archived = False  # unarchive
            room.save()
        if last_message.time < (timezone.now() - td(days=s.DELETE_PUBLIC_CHAT_ROOM)):  # delete after 1 year
            log.info(f'Chat room {room.title} deleted.')
            room.delete()  # delete
            room.save()

    # TODO: Should be a Cron Job. Now it is called with every refresh.
    # Archive/Delete old private chat room
    for room in private_rooms:
        for user in room.allowed.all():
            if not user.is_active:
                room.archived = True
                room.save()
                try:
                    last_message = Message.objects.filter(room_id=room.id).latest('time')
                except Message.DoesNotExist:
                    # TODO This happens only for rooms without messages so not really needed
                    # logger.info(f'Message.DoesNotExist2 in {room}')
                    continue
                if last_message.time < (timezone.now() - td(days=s.DELETE_INACTIVE_USER_AFTER)):  # delete inactive users private room
                    log.info(f'Chat room {room.title} deleted.')
                    room.delete()  # delete
            elif user.is_active:
                room.archived = False
                room.save()

    # Get a list of rooms, ordered alphabetically
    allowed_rooms = Room.objects.filter(allowed=request.user.id).order_by("title")

    # Find out which room to open by default
    last_user_room = None
    messages_by_user = Message.objects.filter(sender=request.user).order_by("-time")
    if messages_by_user.exists():
        last_user_room = messages_by_user.first().room.id

    # Render that in the chat template
    return render(request, "chat/chat.html", {
        'last_used_room': json.dumps(last_user_room),
        'translations': get_translations(),

        'public_active': allowed_rooms.filter(public=True, archived=False).extra(select={'lower_title':'lower(title)'}).order_by('lower_title'),
        'public_archived': allowed_rooms.filter(public=True, archived=True),
        'private_active': allowed_rooms.filter(public=False, archived=False),
        'private_archived': allowed_rooms.filter(public=False, archived=True),

        'user': request.user,
        'ARCHIVE_PUBLIC_CHAT_ROOM': td(days=s.ARCHIVE_PUBLIC_CHAT_ROOM).days,
        'DELETE_PUBLIC_CHAT_ROOM': td(days=s.DELETE_PUBLIC_CHAT_ROOM).days,})


@csrf_exempt
def upload_image(request: HttpRequest):
    filenames = []
    for image in request.FILES.getlist('images'):

        file_type = imghdr.what(image)
        image.seek(0)

        file_bytes = image.read()
        if len(file_bytes) > (s.UPLOAD_IMAGE_MAX_SIZE_MB * 1000000 * 2):
            return JsonResponse({'error': 'file too big'})

        if file_type is None:
            return JsonResponse({'error': 'bad type'})

        filename = f"{uuid.uuid4()}.{file_type}"
        with open(f"{s.BASE_DIR}/media/uploads/{filename}", "wb") as f:
            f.write(file_bytes)
        filenames.append(filename)

    return JsonResponse({'filenames': filenames})


def get_translations():
    _("Click here to enable notifications"),
    _("Today"),
    _("Yesterday"),
    _("Anonymous"),
    _("Enable Notifications"),
    _("Chat works better with notifications. You can allow them to see new messages even beyond chat room."),
    _("Do you want to receive notifications?"),
    _("If nothing happens, you may have ignored permission prompt too many times. Check your browser settings to enable them."),
    _("Yes"),
    _("No, don't show again"),
    _("edit"),
    _("edited"),
    _("Changes History"),
    _("Close"),
    _("This room is empty, be the first one to write something."),
    _("editing: "),
    _("Loading..."),
    _("Sunday"), _("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"),
    _("Jan"), _("Feb"), _("Mar"), _("Apr"), _("May"), _("Jun"), _("Jul"), _("Aug"), _("Sep"), _("Oct"), _("Nov"), _("Dec"),

    strings = [
        "Click here to enable notifications",
        "Today",
        "Yesterday",
        "Anonymous",
        "Enable Notifications",
        "Chat works better with notifications. You can allow them to see new messages even beyond chat room.",
        "Do you want to receive notifications?",
        "If nothing happens, you may have ignored permission prompt too many times. Check your browser settings to enable them.",
        "Yes",
        "No, don't show again",
        "edit",
        "edited",
        "Changes History",
        "Close",
        "This room is empty, be the first one to write something.",
        "editing: ",
        "Loading...",
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    translation = {x: _(x) for x in strings}
    # for i in translation:
    #     print(i, _(i))
    return translation


@receiver(user_accepted)
def create_one2one_rooms(sender, **kwargs):
    # Create all 1to1 rooms
    active_users = User.objects.filter(is_active=True)
    # i = request.user
    # i = kwargs['user']
    for i in active_users:
        for j in active_users:
            # User A will not talk to user A
            if i == j:  
                continue
            # Avoid A-B B-A because it is the same thing
            t = sorted([i.username, j.username])
            title = '-'.join(t)
            existing_room = Room.find_with_users(i, j)

            # check if room for user i and j exists, if so make sure room name is correct
            if existing_room is not None:
                existing_room.title = title
                existing_room.save()
            # if not - create new room
            else:
                try:
                    r = Room.objects.create(title=title, public=False)
                except IntegrityError:
                    r = Room.objects.get(title=title)
                    r.allowed.set((i, j,))


@receiver(user_deleted)
def delete_one2one_rooms(sender, user, **kwargs):
    private_rooms = Room.objects.filter(public=False)
    for room in private_rooms:
        if user.username in room.title:  # TODO: If Public room have name of the user in it - it will be deleted
            log.info(f'Room {room} deleted.')
            room.delete()
