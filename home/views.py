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
from django.db.models import Count, Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

# First party imports
from board.models import Post
from chat.models import Room, Message
from elibrary.models import Book
from glosowania.models import Decyzja, Argument as DecyzjaArgument, KtoJuzGlosowal
from bookkeeping.models import Transaction
from obywatele.models import Uzytkownik, CitizenActivity
from tasks.models import Task
from events.models import Event

# Local folder imports
from .forms import RememberLoginForm
from .models import FeedItem, OnboardingProgress, ReadStatus

log = logging.getLogger(__name__)


def build_read_status_map(user):
    return {
        content_type: set(object_ids)
        for content_type, object_ids in (
            (content_type, ReadStatus.objects.filter(user=user, content_type=content_type).values_list('object_id', flat=True))
            for content_type in ReadStatus.ContentType.values
        )
    }


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
    
    # Check if we should filter to show only unread items
    # Priority: URL parameter > session (synced from localStorage)
    url_filter = request.GET.get('filter')
    
    if url_filter is not None:
        # URL parameter takes precedence
        filter_unread = url_filter == 'unread'
        # Update session to match URL
        request.session['show_unread_only'] = filter_unread
    elif 'show_unread_only' in request.session:
        # Use saved preference from session (synced from localStorage)
        filter_unread = request.session['show_unread_only']
    else:
        # Default: show all items
        filter_unread = False
    
    if filter_unread:
        feed_items = unread_items
    
    # Get counts for each section
    ongoing_count = Decyzja.objects.filter(status=3).count()
    upcoming_count = Decyzja.objects.filter(status=2).count()
    signatures_count = Decyzja.objects.filter(status=1).count()

    # Nowe propozycje widget (max 3, zbierające podpisy)
    new_proposals = Decyzja.objects.filter(status=1).select_related('author').order_by('-data_ostatniej_modyfikacji')[:3]

    # My tasks widget (max 3, active — assigned to me or supported by me)
    my_tasks = Task.objects.filter(
        Q(assigned_to=request.user) |
        Q(votes__user=request.user, votes__value=1)
    ).filter(status=Task.Status.ACTIVE).distinct().order_by('updated_at')[:3]

    # Active referendum widget
    active_referendum = None
    referendum_obj = Decyzja.objects.filter(status=3).select_related('author').order_by('-data_referendum_start').first()
    if referendum_obj and referendum_obj.data_referendum_start and referendum_obj.data_referendum_stop:
        today = timezone.now().date()
        days_remaining = max(0, (referendum_obj.data_referendum_stop - today).days)
        total_days = max(1, (referendum_obj.data_referendum_stop - referendum_obj.data_referendum_start).days)
        time_pct = min(100, round(days_remaining / total_days * 100))
        voters_count = referendum_obj.za + referendum_obj.przeciw
        total_citizens = User.objects.filter(is_active=True).count()
        turnout_pct = round(voters_count / total_citizens * 100) if total_citizens > 0 else 0
        if time_pct > 50:
            bar_color = 'success'
        elif time_pct >= 20:
            bar_color = 'warning'
        else:
            bar_color = 'danger'
        user_voted = KtoJuzGlosowal.objects.filter(
            projekt=referendum_obj,
            ktory_uzytkownik_juz_zaglosowal=request.user,
        ).exists()
        active_referendum = {
            'obj': referendum_obj,
            'voters_count': voters_count,
            'total_citizens': total_citizens,
            'turnout_pct': turnout_pct,
            'days_remaining': days_remaining,
            'total_days': total_days,
            'time_pct': time_pct,
            'bar_color': bar_color,
            'user_voted': user_voted,
        }

    # Karta 4 — Kalendarz: 3 najbliższe aktywne eventy
    today_dt = timezone.now()
    upcoming_events = list(
        Event.objects.filter(start_date__gte=today_dt, is_active=True)
        .order_by('start_date')[:3]
    )

    # Karta 5 — Finanse: przychody/wydatki za bieżący rok
    current_year = today_dt.year
    finance_qs = Transaction.objects.filter(payment_received_date__year=current_year)
    income = finance_qs.filter(type='I').aggregate(total=Sum('amount'))['total'] or 0
    expenses = finance_qs.filter(type='O').aggregate(total=Sum('amount'))['total'] or 0
    balance = income - expenses

    # Karta 6 — Nowi obywatele: 6 ostatnio dołączonych aktywnych
    new_citizens = list(
        Uzytkownik.objects.filter(uid__is_active=True)
        .select_related('uid')
        .order_by('-uid__date_joined')[:7]
    )
    candidates_count = (
        Uzytkownik.objects.filter(uid__is_active=False).count()
        if request.user.is_staff else None
    )

    # Kafelek aktywność — 3 najnowsze pozycje (tylko non-event)
    last_feed_items = [i for i in feed_items if i['content_type'] != 'event'][:3]

    # Onboarding widget
    onboarding = None
    try:
        op = OnboardingProgress.objects.get(user=request.user)
        if not op.completed:
            onboarding = op
    except OnboardingProgress.DoesNotExist:
        onboarding = OnboardingProgress()  # unsaved, all False defaults

    rules_post_pk = getattr(settings, 'ONBOARDING_RULES_POST_ID', None)

    return render(request, 'home/home.html', {
        'feed_items': feed_items,
        'first_unread': first_unread,
        'unread_items': unread_items,
        'filter_unread': filter_unread,
        'ongoing_count': ongoing_count,
        'upcoming_count': upcoming_count,
        'signatures_count': signatures_count,
        'active_referendum': active_referendum,
        'my_tasks': my_tasks,
        'onboarding': onboarding,
        'rules_post_pk': rules_post_pk,
        'upcoming_events': upcoming_events,
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'current_year': current_year,
        'new_citizens': new_citizens,
        'candidates_count': candidates_count,
        'last_feed_items': last_feed_items,
        'new_proposals': new_proposals,
    })


def generate_feed_items(user):
    """Generate unified chronological feed for a user"""
    feed_items = []
    read_status_map = build_read_status_map(user)

    # Get recent posts
    posts = Post.objects.filter(
        updated__gte=timezone.now() - td(days=30)
    ).select_related('author').order_by('-updated')
    
    for post in posts:
        clean_text = strip_tags(post.text)
        feed_items.append({
            'content_type': 'post',
            'title': post.title,
            'description': clean_text[:125] + '...' if len(clean_text) > 125 else clean_text,
            'author': post.author,
            'timestamp': post.updated,
            'url': f"/board/view/{post.pk}/",
            'is_read': post.pk in read_status_map[ReadStatus.ContentType.POST],
            'object_id': post.pk,
        })
    
    # Get recent tasks
    tasks = Task.objects.filter(
        updated_at__gte=timezone.now() - td(days=30)
    ).select_related('created_by', 'assigned_to').order_by('-updated_at')
    
    for task in tasks:
        clean_description = strip_tags(task.description)
        feed_items.append({
            'content_type': 'task',
            'title': task.title,
            'description': clean_description[:125] + '...' if len(clean_description) > 125 else clean_description,
            'author': task.created_by or task.assigned_to,
            'timestamp': task.updated_at,
            'url': f"/tasks/{task.pk}/",
            'is_read': task.pk in read_status_map[ReadStatus.ContentType.TASK],
            'object_id': task.pk,
        })
    
    # Get recent books
    books = Book.objects.filter(
        uploaded__gte=timezone.now() - td(days=30)
    ).select_related('uploader').order_by('-uploaded')
    
    for book in books:
        clean_abstract = strip_tags(book.abstract) if book.abstract else ''
        feed_items.append({
            'content_type': 'book',
            'title': book.title or _('Untitled Book'),
            'description': clean_abstract[:125] + '...' if clean_abstract and len(clean_abstract) > 125 else clean_abstract,
            'author': book.uploader,
            'timestamp': book.uploaded,
            'url': f"/elibrary/{book.pk}/detail/",
            'is_read': book.pk in read_status_map[ReadStatus.ContentType.BOOK],
            'object_id': book.pk,
        })
    
    # Get upcoming events (including periodic events)
    events = Event.objects.filter(is_active=True).select_related()
    
    # Filter events that have upcoming occurrences and get their next occurrence
    upcoming_events = []
    for event in events:
        next_occurrence = event.get_next_occurrence()
        if next_occurrence and next_occurrence >= timezone.now() - td(days=1):
            upcoming_events.append((event, next_occurrence))
    
    # Sort by next occurrence date (nearest first)
    upcoming_events.sort(key=lambda x: x[1])
    
    for event, next_occurrence in upcoming_events:
        clean_description = strip_tags(event.description) if event.description else ''
        feed_items.append({
            'content_type': 'event',
            'title': event.title,
            'description': clean_description[:125] + '...' if clean_description and len(clean_description) > 125 else clean_description,
            'author': None,
            'timestamp': next_occurrence,
            'url': f"/events/{event.pk}/",
            'is_read': event.pk in read_status_map[ReadStatus.ContentType.EVENT],
            'object_id': event.pk,
        })

    # Get recent messages from rooms user has access to, grouped by room
    rooms = Room.objects.filter(allowed=user).prefetch_related('messages', 'messages__sender')
    # Use ReadStatus for room messages consistency
    seen_room_ids = set(ReadStatus.objects.filter(
        user=user, 
        content_type=ReadStatus.ContentType.MESSAGE
    ).values_list('object_id', flat=True))
    
    for room in rooms:
        messages = room.messages.filter(
            time__gte=timezone.now() - td(days=30)
        ).order_by('-time')[:5]  # Get newest messages first
        
        if messages:  # Only add room if it has recent messages
            # Use first message (newest) for timestamp and author
            latest_message = messages[0]
            
            # Reverse messages for chronological display (oldest to newest)
            messages_reversed = list(reversed(messages))
            
            # Create description showing all messages with authors
            message_list = []
            for message in messages_reversed:
                clean_text = strip_tags(message.text)
                if message.sender:
                    author_name = message.sender.username
                else:
                    author_name = 'System'
                message_list.append(f"- <strong>{author_name}:</strong> {clean_text}")
            
            # Join messages with newlines for better readability
            description = '\n'.join(message_list)
            
            feed_items.append({
                'content_type': 'room_messages',
                'title': _("Messages in %(room_title)s") % {'room_title': room.title},
                'description': description,
                'author': latest_message.sender,
                'timestamp': latest_message.time,
                'url': f"/chat/#room_id={room.id}",
                'is_read': room.id in seen_room_ids,  # Room is read if marked as read in ReadStatus
                'object_id': room.id,  # Use room ID as object_id for grouping
                'room_id': room.id,
                'message_count': len(messages),
            })
    
    # Get recent decisions
    decisions = Decyzja.objects.filter(
        data_ostatniej_modyfikacji__gte=timezone.now() - td(days=30)
    ).order_by('-data_ostatniej_modyfikacji')
    
    for decision in decisions:
        clean_tresc = strip_tags(decision.tresc) if decision.tresc else ''
        feed_items.append({
            'content_type': 'decision',
            'title': decision.title,
            'description': clean_tresc[:125] + '...' if clean_tresc and len(clean_tresc) > 125 else clean_tresc,
            'author': decision.author,
            'timestamp': decision.data_ostatniej_modyfikacji,
            'url': f"/glosowania/details/{decision.pk}/",
            'is_read': decision.pk in read_status_map[ReadStatus.ContentType.DECISION],
            'object_id': decision.pk,
        })
    
    # Get recent citizen activities
    citizen_activities = CitizenActivity.objects.filter(
        timestamp__gte=timezone.now() - td(days=30)
    ).select_related('uzytkownik', 'uzytkownik__uid').order_by('-timestamp')
    
    for activity in citizen_activities:
        feed_items.append({
            'content_type': 'citizen',
            'title': activity.get_activity_type_display(),
            'description': f"{activity.uzytkownik.uid.username} - {_(activity.description)}",
            'author': activity.uzytkownik.uid,
            'timestamp': activity.timestamp,
            'url': f"/obywatele/{activity.uzytkownik.uid.id}/",
            'is_read': activity.pk in read_status_map[ReadStatus.ContentType.CITIZEN],
            'object_id': activity.pk,
        })
    
    # Sort all items by timestamp, but events should be in ascending order (nearest first)
    events_items = [item for item in feed_items if item['content_type'] == 'event']
    other_items = [item for item in feed_items if item['content_type'] != 'event']
    
    # Sort events by timestamp ascending (nearest first)
    events_items.sort(key=lambda x: x['timestamp'])
    # Sort other items by timestamp descending (newest first)
    other_items.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Combine: events first (nearest to most distant), then other items (newest to oldest)
    feed_items = events_items + other_items
    
    return feed_items


@login_required
def activity_page(request):
    all_items = generate_feed_items(request.user)

    # Filter by content_type
    ct_filter = request.GET.get('type', '')
    if ct_filter:
        all_items = [i for i in all_items if i['content_type'] == ct_filter]

    # Sort
    sort = request.GET.get('sort', 'date')
    order = request.GET.get('order', 'desc')
    if sort == 'date':
        all_items.sort(key=lambda x: x['timestamp'], reverse=(order == 'desc'))

    content_types = [
        ('', _('Wszystkie')),
        ('post', _('Ogłoszenia')),
        ('task', _('Zadania')),
        ('decision', _('Głosowania')),
        ('event', _('Kalendarz')),
        ('citizen', _('Obywatele')),
        ('book', _('Biblioteka')),
        ('room_messages', _('Czat')),
    ]

    return render(request, 'home/activity.html', {
        'feed_items': all_items,
        'ct_filter': ct_filter,
        'sort': sort,
        'order': order,
        'content_types': content_types,
    })


@login_required
@require_POST
def mark_rules_read(request):
    obj, _ = OnboardingProgress.objects.get_or_create(user=request.user)
    obj.step1_read = True
    obj.save(update_fields=['step1_read'])
    return redirect(request.POST.get('next', '/'))


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
            'room_messages': ReadStatus.ContentType.MESSAGE,  # Map room messages to message type for read tracking
            'decision': ReadStatus.ContentType.DECISION,
            'citizen': ReadStatus.ContentType.CITIZEN,
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
        
        # For room messages, also update room.seen_by for chat consistency
        if content_type in ['message', 'room_messages'] and read_status_content_type == ReadStatus.ContentType.MESSAGE:
            try:
                from chat.models import Room
                room = Room.objects.get(id=object_id)
                room.seen_by.add(request.user)
            except Room.DoesNotExist:
                pass  # Room might not exist, ignore
        
        return JsonResponse({'success': True})
        
    except (ValueError, KeyError):
        return JsonResponse({'success': False, 'error': 'Invalid parameters'})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all feed items as read for the current user"""
    try:
        user = request.user
        
        # Get all current feed items and mark them as read
        feed_items = generate_feed_items(user)
        read_status_map = build_read_status_map(user)
        
        # Create read statuses for all unread items
        created_count = 0
        room_ids_to_mark = []  # Collect room IDs for batch update
        
        for item in feed_items:
            if not item['is_read']:
                content_type_map = {
                    'post': ReadStatus.ContentType.POST,
                    'task': ReadStatus.ContentType.TASK,
                    'book': ReadStatus.ContentType.BOOK,
                    'event': ReadStatus.ContentType.EVENT,
                    'message': ReadStatus.ContentType.MESSAGE,
                    'room_messages': ReadStatus.ContentType.MESSAGE,
                    'decision': ReadStatus.ContentType.DECISION,
                    'citizen': ReadStatus.ContentType.CITIZEN,
                }
                
                read_status_content_type = content_type_map.get(item['content_type'])
                if read_status_content_type:
                    read_status, created = ReadStatus.objects.get_or_create(
                        user=user,
                        content_type=read_status_content_type,
                        object_id=item['object_id']
                    )
                    if created:
                        created_count += 1
                    
                    # Collect room IDs for batch seen_by update
                    if item['content_type'] in ['message', 'room_messages'] and read_status_content_type == ReadStatus.ContentType.MESSAGE:
                        room_ids_to_mark.append(item['object_id'])
        
        # Batch update room.seen_by for all rooms
        if room_ids_to_mark:
            try:
                from chat.models import Room
                rooms = Room.objects.filter(id__in=room_ids_to_mark)
                for room in rooms:
                    room.seen_by.add(user)
            except Exception as e:
                log.warning(f"Could not update room.seen_by: {e}")
        
        return JsonResponse({'success': True, 'marked_count': created_count})
        
    except Exception as e:
        log.error(f"Error marking all as read for user {request.user.id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def save_filter_state(request):
    """Save filter state in session"""
    try:
        filter_state = request.POST.get('show_unread_only', 'false').lower() == 'true'
        request.session['show_unread_only'] = filter_state
        request.session.modified = True
        return JsonResponse({'success': True})
    except Exception as e:
        log.error(f"Error saving filter state: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


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
            'room_messages': ReadStatus.ContentType.MESSAGE,  # Map room messages to message type for read tracking
            'decision': ReadStatus.ContentType.DECISION,
            'citizen': ReadStatus.ContentType.CITIZEN,
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
        
        # For room messages, also remove from room.seen_by for chat consistency
        if content_type in ['message', 'room_messages'] and read_status_content_type == ReadStatus.ContentType.MESSAGE:
            try:
                from chat.models import Room
                room = Room.objects.get(id=object_id)
                room.seen_by.remove(request.user)
            except Room.DoesNotExist:
                pass  # Room might not exist, ignore
        
        return JsonResponse({'success': True})
        
    except (ValueError, KeyError):
        return JsonResponse({'success': False, 'error': 'Invalid parameters'})


ALL_SEARCH_CATS = ['post', 'task', 'decision', 'event', 'book', 'citizen', 'chat']


@login_required
def global_search(request: HttpRequest):
    from django.contrib.auth.models import User as AuthUser
    from chat.models import Room, Message

    query = request.GET.get('q', '').strip()

    # Determine active categories (empty = all)
    selected = [c for c in request.GET.getlist('cat') if c in ALL_SEARCH_CATS]
    active_cats = set(selected) if selected else set(ALL_SEARCH_CATS)

    results = []

    if query:
        # ── Board posts ──────────────────────────────────────────────
        if 'post' in active_cats:
            from django.db.models import Q
            posts = Post.objects.filter(
                Q(title__icontains=query) |
                Q(subtitle__icontains=query) |
                Q(text__icontains=query)
            ).distinct()[:10]
            for obj in posts:
                results.append({
                    'cat': 'post',
                    'type': _('Post'),
                    'type_color': 'primary',
                    'title': obj.title,
                    'description': (strip_tags(obj.text) or '')[:120],
                    'url': f'/board/view/{obj.pk}/',
                })

        # ── Tasks ────────────────────────────────────────────────────
        if 'task' in active_cats:
            from django.db.models import Q
            tasks = Task.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            ).distinct()[:10]
            for obj in tasks:
                results.append({
                    'cat': 'task',
                    'type': _('Task'),
                    'type_color': 'warning',
                    'title': obj.title,
                    'description': (strip_tags(obj.description) or '')[:120],
                    'url': f'/tasks/{obj.pk}/',
                })

        # ── Voting / decisions – all statuses (1=Propozycja … 5=Zatwierdzone) ──
        if 'decision' in active_cats:
            from django.db.models import Q

            # 1. Search main decision fields
            decisions = Decyzja.objects.filter(
                Q(title__icontains=query) |
                Q(tresc__icontains=query) |
                Q(uzasadnienie__icontains=query) |
                Q(args_for__icontains=query) |
                Q(args_against__icontains=query)
            ).distinct()[:10]

            STATUS_LABELS = {
                1: str(_('Proposition')),
                2: str(_('Discussion')),
                3: str(_('Referendum')),
                4: str(_('Rejected')),
                5: str(_('Approved')),
            }

            for obj in decisions:
                matched_field = ''
                q_low = query.lower()
                if q_low in (obj.args_for or '').lower():
                    matched_field = str(_('argument for'))
                elif q_low in (obj.args_against or '').lower():
                    matched_field = str(_('argument against'))
                elif q_low in (obj.uzasadnienie or '').lower():
                    matched_field = str(_('reasoning'))

                snippet = strip_tags(obj.tresc or obj.uzasadnienie or '') or ''
                results.append({
                    'cat': 'decision',
                    'type': _('Voting'),
                    'type_color': 'danger',
                    'title': obj.title,
                    'description': snippet[:120],
                    'meta': (STATUS_LABELS.get(obj.status, '') +
                             (f' · {matched_field}' if matched_field else '')),
                    'url': f'/glosowania/details/{obj.pk}/',
                })

            # 2. Search Argument model (user-added arguments across all statuses)
            arguments_qs = DecyzjaArgument.objects.filter(
                content__icontains=query
            ).select_related('decyzja', 'author').distinct()[:15]

            seen_decision_ids = {r['url'] for r in results if r['cat'] == 'decision'}
            for arg in arguments_qs:
                arg_type_label = (
                    str(_('argument for')) if arg.argument_type == 'FOR'
                    else str(_('argument against'))
                )
                status_label = STATUS_LABELS.get(arg.decyzja.status, '')
                url = f'/glosowania/details/{arg.decyzja.pk}/'
                author_name = arg.author.username if arg.author else str(_('unknown'))
                results.append({
                    'cat': 'decision',
                    'type': _('Voting'),
                    'type_color': 'danger',
                    'title': arg.decyzja.title,
                    'description': arg.content[:120],
                    'meta': f'{status_label} · {arg_type_label} · {author_name}',
                    'url': url,
                })

        # ── Events ───────────────────────────────────────────────────
        if 'event' in active_cats:
            from django.db.models import Q
            events = Event.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(place__icontains=query)
            ).distinct()[:10]
            for obj in events:
                results.append({
                    'cat': 'event',
                    'type': _('Event'),
                    'type_color': 'success',
                    'title': obj.title,
                    'description': (strip_tags(obj.description) or '')[:120],
                    'url': f'/events/{obj.pk}/',
                })

        # ── Library ──────────────────────────────────────────────────
        if 'book' in active_cats:
            from django.db.models import Q
            books = Book.objects.filter(
                Q(title__icontains=query) |
                Q(author__icontains=query) |
                Q(abstract__icontains=query)
            ).distinct()[:10]
            for obj in books:
                results.append({
                    'cat': 'book',
                    'type': _('Library'),
                    'type_color': 'info',
                    'title': obj.title or str(_('Untitled')),
                    'description': (strip_tags(obj.abstract) or '')[:120],
                    'url': f'/elibrary/{obj.pk}/detail/',
                })

        # ── Citizens ─────────────────────────────────────────────────
        if 'citizen' in active_cats:
            from django.db.models import Q
            users = AuthUser.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            ).distinct()[:10]
            for obj in users:
                results.append({
                    'cat': 'citizen',
                    'type': _('Citizen'),
                    'type_color': 'secondary',
                    'title': obj.get_full_name() or obj.username,
                    'description': f'@{obj.username}',
                    'url': f'/obywatele/{obj.pk}/',
                })

        # ── Chat (rooms + messages user has access to) ────────────────
        if 'chat' in active_cats:
            from django.db.models import Q
            accessible_rooms = Room.objects.filter(allowed=request.user)

            # Rooms by title
            rooms = accessible_rooms.filter(title__icontains=query).distinct()[:5]
            for obj in rooms:
                results.append({
                    'cat': 'chat',
                    'type': _('Chat room'),
                    'type_color': 'primary',
                    'title': obj.title,
                    'description': '',
                    'url': f'/chat/#room_id={obj.pk}',
                })

            # Messages in accessible rooms
            messages_qs = Message.objects.filter(
                Q(text__icontains=query),
                room__in=accessible_rooms,
            ).select_related('sender', 'room').order_by('-time').distinct()[:15]
            for obj in messages_qs:
                sender_name = obj.sender.username if obj.sender else str(_('Anonymous'))
                results.append({
                    'cat': 'chat',
                    'type': _('Chat message'),
                    'type_color': 'primary',
                    'title': f'{obj.room.title}',
                    'description': f'{sender_name}: {strip_tags(obj.text)[:100]}',
                    'url': f'/chat/#room_id={obj.room.pk}',
                })

    unread_items = [i for i in generate_feed_items(request.user) if not i['is_read']]
    return render(request, 'home/search.html', {
        'query': query,
        'results': results,
        'active_cats': active_cats,
        'all_cats': ALL_SEARCH_CATS,
        'selected_cats': selected,
        'unread_items': unread_items,
    })


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
