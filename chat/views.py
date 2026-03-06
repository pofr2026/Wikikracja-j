import json
import logging
import uuid

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from chat.models import Room, Message
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
from PIL import Image

log = logging.getLogger(__name__)

@login_required
def add_room(request: HttpRequest):
    """
    Add public chat room
    """    
    if request.method != 'POST':
        return render(request, 'chat/add.html', {'form': RoomForm()})

    form = RoomForm(request.POST)
    if not form.is_valid():
        return render(request, 'chat/add.html', {'form': form})

    room = form.save(commit=False)
    room.last_activity = timezone.now()
    room.save()

    # Allow active user access to new public rooms
    active_users = User.objects.filter(is_active=True)
    public_rooms = Room.objects.filter(public=True)
    for pr in public_rooms:
        pr.allowed.set(active_users)

    return redirect(f"{reverse('chat:chat')}#room_id={room.id}")


@login_required
def chat(request: HttpRequest):
    """
    Root page view. This is essentially a single-page app, if you ignore the
    login and admin parts.
    """

    # Get a list of rooms, ordered alphabetically
    allowed_rooms = Room.objects.filter(allowed=request.user.id).order_by("title")
    public_active= allowed_rooms.filter(public=True, archived=False).prefetch_related("messages")
    # a = list(public_active)
    
    
    public_archived= allowed_rooms.filter(public=True, archived=True).prefetch_related("messages")
    private_active= allowed_rooms.filter(public=False, archived=False).prefetch_related("messages")
    private_archived= allowed_rooms.filter(public=False, archived=True).prefetch_related("messages")
    
    # seen = room.seen_by.filter(id=user.id) or room.messages.all().count() == 0
    
    # Find out which room to open by default
    # messages_by_user = Message.objects.filter(sender=request.user).values("room__id").order_by("-time").first()
    # last_user_room = messages_by_user and messages_by_user["room__id"]
    
    # Render that in the chat template
    return render(request, "chat/chat.html", {
        'last_used_room': json.dumps(None),
        'translations': get_translations(),
        'public_active': public_active,
        'public_archived': public_archived,
        'private_active': private_active,
        'private_archived': private_archived,
        'user': request.user,
        'ARCHIVE_PUBLIC_CHAT_ROOM': td(days=s.ARCHIVE_PUBLIC_CHAT_ROOM).days,
        'DELETE_PUBLIC_CHAT_ROOM': td(days=s.DELETE_PUBLIC_CHAT_ROOM).days,})


def check_image_type(file_path):
    try:
        with Image.open(file_path) as img:
            return img.format.lower()
    except Exception:
        return None

@csrf_exempt
def upload_image(request: HttpRequest):
    filenames = []
    for image in request.FILES.getlist('images'):
        file_type = check_image_type(image)
        if file_type is None:
            return JsonResponse({'error': 'bad type'})
        
        image.seek(0)
        file_bytes = image.read()
        if len(file_bytes) > (s.UPLOAD_IMAGE_MAX_SIZE_MB * 1000000 * 2):
            return JsonResponse({'error': 'file too big'})

        filename = f"{uuid.uuid4()}.{file_type}"
        with open(f"{s.BASE_DIR}/media/uploads/{filename}", "wb") as f:
            f.write(file_bytes)
        filenames.append(filename)

    return JsonResponse({'filenames': filenames})


def get_translations():
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
        "Copy link",
        "Copy message link",
        "Link copied",
        "Could not copy link",
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
                    r.allowed.set((i, j,))
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
