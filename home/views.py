# Standard library imports
import logging
import os
from datetime import datetime as dt
from datetime import timedelta as td

# Third party imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib.staticfiles import finders
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

# First party imports
from board.models import Post
from chat.models import Room, Message
from elibrary.models import Book

# from glosowania.views import ZliczajWszystko
from glosowania.models import Decyzja
from obywatele.models import Uzytkownik
from tasks.models import Task
from events.models import Event

# Local folder imports
from .forms import RememberLoginForm
from .models import FeedItem, ReadStatus

log = logging.getLogger(__name__)


def home(request: HttpRequest):
    if not request.user.is_authenticated:
        start = Post.objects.filter(title='Start').order_by('-updated', '-created').first()
        if not start:
            log.info('Add Board Message title Start.')
            start = ''
        return render(request, 'home/home.html', {'start': start})
    
    # Generate unified feed
    feed_items = generate_feed_items(request.user)
    
    # Find first unread item for jump functionality
    first_unread = None
    unread_items = [item for item in feed_items if not item['is_read']]
    if unread_items:
        first_unread = unread_items[0]
        # Mark the first unread item with ID for jumping
        for i, item in enumerate(feed_items):
            if item == first_unread:
                feed_items[i]['is_first_unread'] = True
                break
    
    # Get counts for each section
    ongoing_count = Decyzja.objects.filter(status=3).count()
    upcoming_count = Decyzja.objects.filter(status=2).count()
    signatures_count = Decyzja.objects.filter(status=1).count()
    
    return render(request, 'home/home.html', {
        'feed_items': feed_items,
        'first_unread': first_unread,
        'ongoing_count': ongoing_count,
        'upcoming_count': upcoming_count,
        'signatures_count': signatures_count,
    })


def generate_feed_items(user):
    """Generate unified chronological feed for a user"""
    feed_items = []
    
    # Get recent posts
    posts = Post.objects.filter(
        updated__gte=timezone.now() - td(days=30)
    ).select_related('author').order_by('-updated')
    
    for post in posts:
        feed_items.append({
            'content_type': 'post',
            'title': post.title,
            'description': post.text[:500] + '...' if len(post.text) > 500 else post.text,
            'author': post.author,
            'timestamp': post.updated,
            'url': f"/board/view/{post.pk}/",
            'is_read': is_post_read_by_user(post, user),
            'object_id': post.pk,
        })
    
    # Get recent tasks
    tasks = Task.objects.filter(
        updated_at__gte=timezone.now() - td(days=30)
    ).select_related('created_by', 'assigned_to').order_by('-updated_at')
    
    for task in tasks:
        feed_items.append({
            'content_type': 'task',
            'title': task.title,
            'description': task.description[:500] + '...' if len(task.description) > 500 else task.description,
            'author': task.created_by or task.assigned_to,
            'timestamp': task.updated_at,
            'url': f"/tasks/{task.pk}/",
            'is_read': is_task_read_by_user(task, user),
            'object_id': task.pk,
        })
    
    # Get recent books
    books = Book.objects.filter(
        uploaded__gte=timezone.now() - td(days=30)
    ).select_related('uploader').order_by('-uploaded')
    
    for book in books:
        feed_items.append({
            'content_type': 'book',
            'title': book.title or _('Untitled Book'),
            'description': book.abstract[:500] + '...' if book.abstract and len(book.abstract) > 500 else (book.abstract or ''),
            'author': book.uploader,
            'timestamp': book.uploaded,
            'url': f"/elibrary/{book.pk}/detail/",
            'is_read': is_book_read_by_user(book, user),
            'object_id': book.pk,
        })
    
    # Get upcoming events (including those starting within 1 day)
    events = Event.objects.filter(
        is_active=True,
        start_date__gte=timezone.now() - td(days=1)
    ).order_by('-start_date')
    
    for event in events:
        feed_items.append({
            'content_type': 'event',
            'title': event.title,
            'description': event.description[:500] + '...' if event.description and len(event.description) > 500 else (event.description or ''),
            'author': None,
            'timestamp': event.start_date,
            'url': f"/events/{event.pk}/",
            'is_read': is_event_read_by_user(event, user),
            'object_id': event.pk,
        })
    
    # Get recent messages from rooms user has access to
    rooms = Room.objects.filter(allowed=user).prefetch_related('messages', 'messages__sender')
    for room in rooms:
        messages = room.messages.filter(
            time__gte=timezone.now() - td(days=30)
        ).order_by('-time')[:5]  # Limit to recent messages per room
        
        for message in messages:
            feed_items.append({
                'content_type': 'message',
                'title': f"Message in {room.title}",
                'description': message.text[:500] + '...' if len(message.text) > 500 else message.text,
                'author': message.sender,
                'timestamp': message.time,
                'url': f"/chat/#room_id={room.id}",
                'is_read': is_message_read_by_user(message, user, room),
                'object_id': message.pk,
                'room_id': room.id,
            })
    
    # Get recent decisions
    decisions = Decyzja.objects.filter(
        data_ostatniej_modyfikacji__gte=timezone.now() - td(days=30)
    ).order_by('-data_ostatniej_modyfikacji')
    
    for decision in decisions:
        feed_items.append({
            'content_type': 'decision',
            'title': decision.title,
            'description': '',  # Decisions don't have description field
            'author': decision.author,
            'timestamp': decision.data_ostatniej_modyfikacji,
            'url': f"/glosowania/details/{decision.pk}/",
            'is_read': is_decision_read_by_user(decision, user),
            'object_id': decision.pk,
        })
    
    # Sort all items by timestamp
    feed_items.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return feed_items


def is_post_read_by_user(post, user):
    """Check if user has read this post"""
    return ReadStatus.objects.filter(
        user=user,
        content_type=ReadStatus.ContentType.POST,
        object_id=post.pk
    ).exists()


def is_task_read_by_user(task, user):
    """Check if user has read this task"""
    return ReadStatus.objects.filter(
        user=user,
        content_type=ReadStatus.ContentType.TASK,
        object_id=task.pk
    ).exists()


def is_book_read_by_user(book, user):
    """Check if user has read this book"""
    return ReadStatus.objects.filter(
        user=user,
        content_type=ReadStatus.ContentType.BOOK,
        object_id=book.pk
    ).exists()


def is_event_read_by_user(event, user):
    """Check if user has read this event"""
    return ReadStatus.objects.filter(
        user=user,
        content_type=ReadStatus.ContentType.EVENT,
        object_id=event.pk
    ).exists()


def is_message_read_by_user(message, user, room):
    """Check if user has read this message"""
    return ReadStatus.objects.filter(
        user=user,
        content_type=ReadStatus.ContentType.MESSAGE,
        object_id=message.pk
    ).exists() or room.seen_by.filter(id=user.id).exists()


def is_decision_read_by_user(decision, user):
    """Check if user has read this decision"""
    return ReadStatus.objects.filter(
        user=user,
        content_type=ReadStatus.ContentType.DECISION,
        object_id=decision.pk
    ).exists()


@login_required
@require_POST
def mark_as_read(request):
    """Mark a feed item as read"""
    content_type = request.POST.get('content_type')
    object_id = request.POST.get('object_id')
    
    if not content_type or not object_id:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    try:
        object_id = int(object_id)
        # Map content types to ReadStatus content types
        content_type_map = {
            'post': ReadStatus.ContentType.POST,
            'task': ReadStatus.ContentType.TASK,
            'book': ReadStatus.ContentType.BOOK,
            'event': ReadStatus.ContentType.EVENT,
            'message': ReadStatus.ContentType.MESSAGE,
            'decision': ReadStatus.ContentType.DECISION,
        }
        
        read_status_content_type = content_type_map.get(content_type)
        if not read_status_content_type:
            return JsonResponse({'success': False, 'error': 'Invalid content type'})
        
        # Create or update read status
        read_status, created = ReadStatus.objects.get_or_create(
            user=request.user,
            content_type=read_status_content_type,
            object_id=object_id
        )
        
        return JsonResponse({'success': True})
        
    except (ValueError, KeyError):
        return JsonResponse({'success': False, 'error': 'Invalid parameters'})


@login_required
@require_POST
def mark_unread(request):
    """Mark a feed item as unread"""
    content_type = request.POST.get('content_type')
    object_id = request.POST.get('object_id')
    
    if not content_type or not object_id:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    try:
        object_id = int(object_id)
        # Map content types to ReadStatus content types
        content_type_map = {
            'post': ReadStatus.ContentType.POST,
            'task': ReadStatus.ContentType.TASK,
            'book': ReadStatus.ContentType.BOOK,
            'event': ReadStatus.ContentType.EVENT,
            'message': ReadStatus.ContentType.MESSAGE,
            'decision': ReadStatus.ContentType.DECISION,
        }
        
        read_status_content_type = content_type_map.get(content_type)
        if not read_status_content_type:
            return JsonResponse({'success': False, 'error': 'Invalid content type'})
        
        # Delete read status to mark as unread
        deleted_count, _ = ReadStatus.objects.filter(
            user=request.user,
            content_type=read_status_content_type,
            object_id=object_id
        ).delete()
        
        return JsonResponse({'success': True})
        
    except (ValueError, KeyError):
        return JsonResponse({'success': False, 'error': 'Invalid parameters'})


class RememberLoginView(LoginView):
    form_class = RememberLoginForm
    template_name = 'home/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        remember = form.cleaned_data.get("remember_me")
        if remember:
            self.request.session.set_expiry(getattr(settings, "REMEMBER_ME_COOKIE_AGE", settings.SESSION_COOKIE_AGE))
        else:
            self.request.session.set_expiry(0)
        return response


@login_required
def haslo(request: HttpRequest):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, _('Your password has been changed.'))
            return redirect('obywatele:my_profile')
        else:
            messages.error(request, _('You typed something wrong. See what error appeared above and try again.'))
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'home/haslo.html', {
        'form': form
    })


def manifest(request):
    """Serve dynamic PWA manifest JSON"""
    data = {
        'name': settings.SITE_NAME,
        'short_name': settings.SITE_NAME_MAX_12_CHARS,
        'description': settings.SITE_DESCRIPTION,
        'start_url': '/',
        'display': 'standalone',
        'orientation': 'any',
        'theme_color': '#375a7f',
        'background_color': '#000',
        "prefer_related_applications": False,
        "related_applications": [],
        'icons': [{
            'src': '/static/home/images/favicon.ico',
            'sizes': "16x16 32x32 48x48",
            'type': 'image/x-icon',
            "purpose": "any"
        }, {
            'src': '/static/home/images/icon-192.png',
            'sizes': "192x192",
            'type': 'image/png',
            "purpose": "any"
        }, {
            'src': '/static/home/images/icon-512.png',
            'sizes': "512x512",
            'type': 'image/png',
            "purpose": "any"
        }],
    }
    return JsonResponse(data, json_dumps_params={
        'ensure_ascii': False
    })


def service_worker(request):
    """Serve the service worker JavaScript file with correct MIME type"""
    sw_path = os.path.join(settings.BASE_DIR, 'chat', 'static', 'chat', 'js', 'sw.js')

    # For development, serve from staticfiles dirs
    if not os.path.exists(sw_path):
        # Try finding in staticfiles dirs
        sw_path = finders.find('chat/js/sw.js')
        if not sw_path:
            return HttpResponse("Service Worker not found", status=404)

    with open(sw_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/javascript')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Service-Worker-Allowed'] = "/"
        return response
