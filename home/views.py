from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
# from glosowania.views import ZliczajWszystko
from glosowania.models import Decyzja
from obywatele.models import Uzytkownik
from board.models import Post
from elibrary.models import Book
from django.contrib.auth.models import User
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from datetime import datetime as dt
from datetime import timedelta as td
from django.utils import timezone
from django.http import HttpRequest
from tasks.models import Task
from chat.models import Room
from .forms import RememberLoginForm
import logging

log = logging.getLogger(__name__)
logging.basicConfig(filename='/var/log/wiki.log', datefmt='%d-%b-%y %H:%M:%S', format='%(asctime)s %(levelname)s %(funcName)s() %(message)s', level=logging.INFO)

def home(request: HttpRequest):
    ongoing = Decyzja.objects.filter(status=3).order_by('data_referendum_start')
    upcoming = Decyzja.objects.filter(status=2).order_by('data_referendum_start')
    signatures = Decyzja.objects.filter(status=1).order_by('data_powstania')

    # Show active users younger than 30 days
    people = Uzytkownik.objects.filter(uid__is_active=True, data_przyjecia__gte=dt.today()-td(days=30))
    # Show inactive users
    people_waiting = User.objects.filter(is_active=False)

    posts = Post.objects.filter(updated__gte=timezone.now()-td(days=30)).order_by('-updated')
    books = Book.objects.filter(uploaded__gte=timezone.now()-td(days=30))

    tasks_in_progress = Task.objects.none()
    tasks_new = Task.objects.none()
    rooms_with_new_messages = Room.objects.none()

    if request.user.is_authenticated:
        tasks_in_progress = Task.objects.filter(
            status=Task.Status.ACTIVE,
            assigned_to__isnull=False,
        ).order_by('-updated_at')[:10]

        tasks_new = Task.objects.filter(
            status=Task.Status.ACTIVE,
            assigned_to__isnull=True,
        ).order_by('-created_at')[:10]

        rooms_with_new_messages = (
            Room.objects.filter(allowed=request.user)
            .exclude(seen_by=request.user)
            .annotate(messages_count=Count('messages'))
            .filter(messages_count__gt=0)
            .order_by('-last_activity')[:10]
        )

    try:
        start = Post.objects.get(title='Start')
    except Exception as e:
        log.info(f'Add Board Message title Start. Exception: {e}')
        start=''
        
    # data_referendum_start = ZliczajWszystko.kolejka
    return render(request,
                  'home/home.html',
                  {
                      'ongoing': ongoing,
                      'upcoming': upcoming,
                      'signatures': signatures,
                      'start': start,
                      'people': people,
                      'people_waiting': people_waiting,
                      'posts': posts,
                      'books': books,
                      'tasks_in_progress': tasks_in_progress,
                      'tasks_new': tasks_new,
                      'rooms_with_new_messages': rooms_with_new_messages,
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
