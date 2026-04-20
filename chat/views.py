# Standard library imports
import json
import logging
import uuid
from datetime import timedelta as td

# Third party imports
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.dispatch import receiver
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from PIL import Image

# First party imports
from chat.forms import RoomForm
from chat.models import Message, Room
from chat.signals import user_accepted, user_deleted

log = logging.getLogger(__name__)


@login_required
def add_room(request: HttpRequest):
    """
    Add public chat room
    """
    if request.method != 'POST':
        return render(request, 'chat/add.html', {
            'form': RoomForm()
        })

    form = RoomForm(request.POST)
    if not form.is_valid():
        return render(request, 'chat/add.html', {
            'form': form
        })

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
    # Optimize queries by:
    # 1. Prefetch allowed users for private rooms (needed for displayed_name)
    # 2. Annotate with message count (for seen_by filter)
    # 3. Annotate with is_seen status (for seen_by filter)
    allowed_rooms = Room.objects.filter(allowed=request.user.id).prefetch_related(Prefetch('allowed', queryset=User.objects.only('id', 'username')), 'muted_by', 'tracked_by').annotate(messages_count=Count('messages'), is_seen=Exists(Room.seen_by.through.objects.filter(room_id=OuterRef('pk'), user_id=request.user.id))).order_by("title")

    public_active = allowed_rooms.filter(public=True, archived=False)
    public_archived = allowed_rooms.filter(public=True, archived=True)
    private_active = allowed_rooms.filter(public=False, archived=False)
    private_archived = allowed_rooms.filter(public=False, archived=True)

    # Split public rooms into categories based on database relations
    from tasks.models import Task
    from glosowania.models import Decyzja

    task_room_ids = Task.objects.filter(chat_room__isnull=False).values_list('chat_room_id', flat=True)
    vote_room_ids = Decyzja.objects.filter(chat_room__isnull=False).values_list('chat_room_id', flat=True)

    public_rooms_active = public_active.exclude(id__in=task_room_ids).exclude(id__in=vote_room_ids)
    public_rooms_archived = public_archived.exclude(id__in=task_room_ids).exclude(id__in=vote_room_ids)

    # ZMIANA 1: querysets drzewa — obiekty Task/Decyzja z chat_room
    tasks_tree_active = Task.objects.filter(
        chat_room__isnull=False,
        chat_room__allowed=request.user,
        chat_room__archived=False,
    ).select_related('chat_room').prefetch_related(
        Prefetch('chat_room__seen_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__muted_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__tracked_by', queryset=User.objects.only('id')),
    ).order_by('title')

    tasks_tree_archived = Task.objects.filter(
        chat_room__isnull=False,
        chat_room__allowed=request.user,
        chat_room__archived=True,
    ).select_related('chat_room').prefetch_related(
        Prefetch('chat_room__seen_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__muted_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__tracked_by', queryset=User.objects.only('id')),
    ).order_by('title')

    votes_tree_active = Decyzja.objects.filter(
        chat_room__isnull=False,
        chat_room__allowed=request.user,
        chat_room__archived=False,
    ).select_related('chat_room').prefetch_related(
        Prefetch('chat_room__seen_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__muted_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__tracked_by', queryset=User.objects.only('id')),
    ).order_by('title')

    votes_tree_archived = Decyzja.objects.filter(
        chat_room__isnull=False,
        chat_room__allowed=request.user,
        chat_room__archived=True,
    ).select_related('chat_room').prefetch_related(
        Prefetch('chat_room__seen_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__muted_by', queryset=User.objects.only('id')),
        Prefetch('chat_room__tracked_by', queryset=User.objects.only('id')),
    ).order_by('title')

    # For "participated only" visual mute: get rooms where user has sent a message
    participated_only = getattr(request.user.uzytkownik, 'email_notifications_chat_participated', False)
    participated_room_ids = set()
    if participated_only:
        participated_room_ids = set(
            Message.objects.filter(sender=request.user).values_list('room_id', flat=True).distinct()
        )

    # Render that in the chat template
    return render(request, "chat/chat.html", {
        'translations': get_translations(),
        'public_rooms_active': public_rooms_active,
        'public_rooms_archived': public_rooms_archived,
        'tasks_tree_active': tasks_tree_active,
        'tasks_tree_archived': tasks_tree_archived,
        'votes_tree_active': votes_tree_active,
        'votes_tree_archived': votes_tree_archived,
        'private_active': private_active,
        'private_archived': private_archived,
        'user': request.user,
        'participated_only': participated_only,
        'participated_room_ids': participated_room_ids,
        'ARCHIVE_PUBLIC_CHAT_ROOM': td(days=settings.ARCHIVE_PUBLIC_CHAT_ROOM).days,
        'DELETE_PUBLIC_CHAT_ROOM': td(days=settings.DELETE_PUBLIC_CHAT_ROOM).days,
        'MESSAGE_MAX_LENGTH': settings.MESSAGE_MAX_LENGTH,
    })


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
            return JsonResponse({
                'error': 'bad type'
            })

        image.seek(0)
        file_bytes = image.read()
        if len(file_bytes) > (settings.UPLOAD_IMAGE_MAX_SIZE_MB * 1000000 * 2):
            return JsonResponse({
                'error': 'file too big'
            })

        filename = f"{uuid.uuid4()}.{file_type}"
        with open(f"{settings.BASE_DIR}/media/uploads/{filename}", "wb") as f:
            f.write(file_bytes)
        filenames.append(filename)

    return JsonResponse({
        'filenames': filenames
    })


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
        "Divide the message into several parts...",
        "Upvote",
        "Downvote",
        "Title",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Unread",
        "Show only unread rooms",
    ]
    translation = {
        x: _(x) for x in strings
    }
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
                    r.allowed.set((
                        i,
                        j,
                    ))
                except IntegrityError:
                    r = Room.objects.get(title__iexact=title)
                    r.allowed.set((
                        i,
                        j,
                    ))


@receiver(user_deleted)
def delete_one2one_rooms(sender, user, **kwargs):
    private_rooms = Room.objects.filter(public=False)
    for room in private_rooms:
        if user.username in room.title:  # TODO: If Public room have name of the user in it - it will be deleted
            log.info(f"Room {room} deleted.")
            room.delete()


@login_required
def room_data(request: HttpRequest, room_id: int):
    """
    JSON endpoint for embedded chat widget.
    Returns room metadata and translations needed by chat-embedded.js.
    """
    try:
        room = Room.objects.get(id=room_id, allowed=request.user)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    return JsonResponse({
        'room_id': room.id,
        'title': room.title,
        'translations': get_translations(),
    })


@login_required
def toggle_notifications(request: HttpRequest):
    """
    Toggle notifications for a room (HTTP fallback for WebSocket handler).
    POST parameters:
    - room_id: ID of the room
    - enabled: boolean (true/false) - true to enable, false to disable
    """
    if request.method != 'POST':
        return JsonResponse({
            'error': 'Method not allowed'
        }, status=405)

    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        enabled = data.get('enabled')

        if room_id is None or enabled is None:
            return JsonResponse({
                'error': 'Missing room_id or enabled parameter'
            }, status=400)

        room = Room.objects.get(id=room_id)

        # Check if user is allowed in this room
        if not room.allowed.filter(id=request.user.id).exists():
            return JsonResponse({
                'error': 'Access denied'
            }, status=403)

        # Add or remove user from muted_by list
        if enabled:
            # Enable notifications: remove from muted_by
            if room.muted_by.filter(id=request.user.id).exists():
                room.muted_by.remove(request.user)
                log.info(f"User {request.user.id} enabled notifications for room {room_id}")
        else:
            # Disable notifications: add to muted_by
            if not room.muted_by.filter(id=request.user.id).exists():
                room.muted_by.add(request.user)
                log.info(f"User {request.user.id} muted notifications for room {room_id}")

        return JsonResponse({
            'success': True,
            'room_id': room_id,
            'notifications_enabled': not room.muted_by.filter(id=request.user.id).exists()
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except Exception as e:
        log.error(f"Error toggling notifications: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def toggle_track(request: HttpRequest):
    """Toggle tracking of a room for the current user."""
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        tracked = data.get('tracked')
        if room_id is None or tracked is None:
            return JsonResponse({'error': 'Missing room_id or tracked'}, status=400)
        room = get_object_or_404(Room, id=room_id, allowed=request.user)
        if tracked:
            room.tracked_by.add(request.user)
        else:
            room.tracked_by.remove(request.user)
        return JsonResponse({'success': True, 'tracked': tracked})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
