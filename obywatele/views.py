# Standard library imports
import logging
import time
from datetime import timedelta

# Third party imports
from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed, user_signed_up
from django.conf import settings as s
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.messages import error, success
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import DatabaseError
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.dispatch import receiver
from django.http import HttpRequest, JsonResponse
from django.utils import timezone, translation
from django.utils.translation import check_for_language
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

# First party imports
from obywatele.filters import UzytkownikFilter
from obywatele.forms import AvatarForm, EmailChangeForm, OnboardingDetailsForm, ProfileForm, SendEmailToAll, UserForm, UsernameChangeForm
from obywatele.models import CitizenActivity, Rate, Uzytkownik
from obywatele.tables import UzytkownikTable
from zzz.utils import build_site_url, get_site_domain

HOST = get_site_domain()

log = logging.getLogger(__name__)

signer = TimestampSigner()


def is_email_confirmed_for_candidate(user: User, profile: Uzytkownik) -> bool:
    if profile.polecajacy:
        return True
    return EmailAddress.objects.filter(user=user, verified=True).exists()


def get_onboarding_user_from_request(request: HttpRequest):
    """
    CRITICAL: Find user for onboarding form access.
    
    DESIGN NOTE: Three ways to access onboarding form:
    1. Session (immediate after signup) - primary method
    2. Email link with uid/token (backup after email confirmation)
    3. Fallback for already active users with incomplete onboarding
    
    Without this logic, users get "Could not find your onboarding account" error.
    """
    onboarding_user_id = request.session.get('onboarding_user_id')

    # METHOD 2: Email link with signed token (backup method)
    uid = request.GET.get('uid')
    token = request.GET.get('token')
    if uid and token:
        try:
            signed_value = signer.unsign(token, max_age=s.DELETE_INACTIVE_USER_AFTER * 24 * 60 * 60)
            if signed_value == str(uid):
                onboarding_user_id = int(uid)
                request.session['onboarding_user_id'] = onboarding_user_id
                request.session.modified = True
        except (BadSignature, SignatureExpired, ValueError):
            onboarding_user_id = None

    if not onboarding_user_id:
        return None

    # METHOD 1: Standard flow - inactive user (just signed up)
    user = User.objects.filter(pk=onboarding_user_id, is_active=False).first()
    if user:
        return user
    
    # METHOD 3: Fallback - active user with incomplete onboarding
    # This handles edge cases where user became active but didn't complete onboarding
    user = User.objects.filter(pk=onboarding_user_id).first()
    if user and hasattr(user, 'uzytkownik'):
        profile = user.uzytkownik
        if profile.onboarding_status in [
            Uzytkownik.OnboardingStatus.EMAIL_ENTERED,
            Uzytkownik.OnboardingStatus.EMAIL_CONFIRMED
        ]:
            return user
    
    return None


def population():
    try:
        population = User.objects.filter(is_active=True).count()
        return population
    except DatabaseError:
        log.exception("Could not calculate population.")
        return 0


def required_reputation():
    if population() <= s.ACCEPTANCE * 2:
        return population() - s.ACCEPTANCE
    if population() > s.ACCEPTANCE * 2:
        return s.ACCEPTANCE
    '''
    Załóżmy, że próg akceptacji wynosi 3.
    W grupie pojawiają się po kolei 1, 2, 3 osoby.
    W takiej sytuacji nikt nie może osiągnąć progu akceptacji wynoszącego 3 bo w grupie są np. 2 osoby.
    Musi więc istnieć mechanizm, który chwilowo obniża próg akceptacji.

    Rozwiązanie:
    populacja - docelowy_próg_akceptacji = chwilowy_próg_akceptacji
    1 -> 1-3=-2
    2 -> 2-3=-1
    3 -> 3-3=0
    4 -> 4-3=+1
    5 -> 5-3=+2
    6 -> 6-3=+3
    7 -> 7-3=+3
    8 -> 8-3=+3

    To rozwiązanie rodzi następny problem:
    Ponieważ próg akceptacji rośnie,
    ale pierwszej osobie w grupie nikt nie dał Akceptuję,
    to po automatycznym podniesieniu progu - pierwsza osoba jest usuwana.

    Stąd bierze się mechanizm automatycznego nadawania istniejącym osobom punktów reputacji.
    '''


@login_required
def parameters(request: HttpRequest):
    return render(request, 'obywatele/parameters.html', {
        'population': population(),
        'acceptance': s.ACCEPTANCE,
        'delete_inactive_user_after': s.DELETE_INACTIVE_USER_AFTER,
    })


def _build_calendar_grid(year, month, events):
    """
    Returns a list of weeks; each week is a list of dicts:
      {'day': int or None, 'events': [Event, ...], 'is_today': bool}
    Days from adjacent months are represented as None.
    """
    import calendar as cal_mod
    from datetime import date

    today = timezone.localdate()
    days_in_month = cal_mod.monthrange(year, month)[1]

    # Build mapping: day_number -> [Event]
    events_by_day = {}
    for event in events:
        freq = event.frequency
        sd = timezone.localtime(event.start_date)

        if freq == 'once':
            if sd.year == year and sd.month == month:
                events_by_day.setdefault(sd.day, []).append(event)

        elif freq == 'daily':
            for d in range(1, days_in_month + 1):
                events_by_day.setdefault(d, []).append(event)

        elif freq == 'weekly':
            target_weekday = sd.weekday()  # 0=Mon
            for d in range(1, days_in_month + 1):
                if date(year, month, d).weekday() == target_weekday:
                    events_by_day.setdefault(d, []).append(event)

        elif freq == 'monthly':
            if sd.day <= days_in_month:
                events_by_day.setdefault(sd.day, []).append(event)

        elif freq == 'monthly_ordinal':
            occurrence = event._get_nth_weekday_of_month(
                year, month, event.monthly_weekday, event.monthly_ordinal
            )
            if occurrence:
                d = timezone.localtime(occurrence).day
                events_by_day.setdefault(d, []).append(event)

        elif freq == 'yearly':
            if sd.month == month:
                if sd.day <= days_in_month:
                    events_by_day.setdefault(sd.day, []).append(event)

    # Build weeks grid (Monday first, 0 = padding)
    raw_weeks = cal_mod.monthcalendar(year, month)
    weeks = []
    for raw_week in raw_weeks:
        week = []
        for day_num in raw_week:
            if day_num == 0:
                week.append({'day': None, 'events': [], 'is_today': False})
            else:
                week.append({
                    'day': day_num,
                    'events': events_by_day.get(day_num, []),
                    'is_today': date(year, month, day_num) == today,
                })
        weeks.append(week)
    return weeks


@login_required
@login_required
def wspolnota_calendar(request: HttpRequest):
    import calendar as cal_mod
    from events.models import Event
    now = timezone.localtime(timezone.now())
    month_param = request.GET.get('month', '')
    try:
        cal_year, cal_month = (int(x) for x in month_param.split('-'))
        if not (1 <= cal_month <= 12):
            raise ValueError
    except (ValueError, AttributeError):
        cal_year, cal_month = now.year, now.month
    events_qs = Event.objects.filter(is_active=True)
    cal_weeks = _build_calendar_grid(cal_year, cal_month, events_qs)
    if cal_month == 1:
        prev_month = f'{cal_year - 1}-12'
    else:
        prev_month = f'{cal_year}-{cal_month - 1:02d}'
    if cal_month == 12:
        next_month = f'{cal_year + 1}-01'
    else:
        next_month = f'{cal_year}-{cal_month + 1:02d}'
    return render(request, 'obywatele/_calendar_partial.html', {
        'cal_weeks': cal_weeks,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': cal_mod.month_name[cal_month],
        'prev_month': prev_month,
        'next_month': next_month,
    })


def wspolnota(request: HttpRequest):
    import calendar as cal_mod
    from bookkeeping.models import Transaction
    from django.db.models import Sum
    from events.models import Event

    # --- stats ---
    thirty_days_ago = timezone.now() - timedelta(days=30)
    pop = population()
    active_last_month = User.objects.filter(is_active=True, last_login__gte=thirty_days_ago).count()
    active_pct = round(active_last_month / pop * 100) if pop else 0
    pending_count = User.objects.filter(is_active=False).count()

    # --- assets & skills ---
    skills_count = Uzytkownik.objects.exclude(skills__isnull=True).exclude(skills='').count()
    knowledge_count = Uzytkownik.objects.exclude(knowledge__isnull=True).exclude(knowledge='').count()
    give_away_count = Uzytkownik.objects.exclude(to_give_away__isnull=True).exclude(to_give_away='').count()
    borrow_count = Uzytkownik.objects.exclude(to_borrow__isnull=True).exclude(to_borrow='').count()
    for_sale_count = Uzytkownik.objects.exclude(for_sale__isnull=True).exclude(for_sale='').count()

    # --- recent members ---
    recent_members = (
        User.objects
        .filter(is_active=True)
        .select_related('uzytkownik')
        .order_by('-uzytkownik__data_przyjecia')[:5]
    )

    # --- recent chat messages ---
    from chat.models import Message
    recent_chat_messages = (
        Message.objects
        .filter(room__public=True, room__allowed=request.user)
        .select_related('sender', 'sender__uzytkownik', 'room')
        .order_by('-time')[:4]
    )

    # --- finances ---
    this_year = timezone.now().year
    income = Transaction.objects.filter(
        type=Transaction.INCOMING, created_date__year=this_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    expense = Transaction.objects.filter(
        type=Transaction.OUTGOING, created_date__year=this_year
    ).aggregate(total=Sum('amount'))['total'] or 0

    # --- calendar ---
    now = timezone.localtime(timezone.now())
    month_param = request.GET.get('month', '')
    try:
        cal_year, cal_month = (int(x) for x in month_param.split('-'))
        if not (1 <= cal_month <= 12):
            raise ValueError
    except (ValueError, AttributeError):
        cal_year, cal_month = now.year, now.month

    events_qs = Event.objects.filter(is_active=True)
    cal_weeks = _build_calendar_grid(cal_year, cal_month, events_qs)

    # prev / next month strings
    if cal_month == 1:
        prev_month = f'{cal_year - 1}-12'
    else:
        prev_month = f'{cal_year}-{cal_month - 1:02d}'
    if cal_month == 12:
        next_month = f'{cal_year + 1}-01'
    else:
        next_month = f'{cal_year}-{cal_month + 1:02d}'

    month_name = cal_mod.month_name[cal_month]

    return render(request, 'obywatele/wspolnota.html', {
        'member_count': pop,
        'active_pct': active_pct,
        'pending_count': pending_count,
        'skills_count': skills_count,
        'knowledge_count': knowledge_count,
        'give_away_count': give_away_count,
        'borrow_count': borrow_count,
        'for_sale_count': for_sale_count,
        'recent_members': recent_members,
        'recent_chat_messages': recent_chat_messages,
        'income': income,
        'expense': expense,
        'balance': income - expense,
        'current_year': this_year,
        'cal_weeks': cal_weeks,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': month_name,
        'prev_month': prev_month,
        'next_month': next_month,
    })


@login_required()
def change_email(request: HttpRequest):
    form = EmailChangeForm(request.user)
    if request.method == 'POST':
        form = EmailChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            message = _("Your new email has been saved.")
            success(request, (message))
            return redirect('obywatele:my_profile')
        else:
            message = form.non_field_errors().as_text() or next(iter(form.errors.values()))
            error(request, (message))
            return redirect('obywatele:my_profile')
    else:
        return render(request, 'obywatele/change_email.html', {
            'form': form
        })


@login_required()
def change_username(request: HttpRequest):
    form = UsernameChangeForm(request.POST)
    if request.method == 'POST':
        form = UsernameChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            message = _("Your name has been saved.")
            success(request, (message))
            return redirect('obywatele:my_profile')
        else:
            message = form.errors
            error(request, (message))
            return redirect('obywatele:my_profile')
    else:
        return render(request, 'obywatele/change_username.html', {
            'form': form
        })


@login_required
def obywatele(request: HttpRequest):
    allowed_sort_fields = {
        'username': 'username',
        'email': 'email',
        'phone': 'uzytkownik__phone',
        'last_login': 'last_login',
        'city': 'uzytkownik__city',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'joined': 'uzytkownik__data_przyjecia',
    }
    blank_sort_fields = {
        'username': 'username_is_blank',
        'email': 'email_is_blank',
        'phone': 'phone_is_blank',
        'last_login': 'last_login_is_blank',
        'city': 'city_is_blank',
        'first_name': 'first_name_is_blank',
        'last_name': 'last_name_is_blank',
        'joined': 'joined_is_blank',
    }
    default_sort = '-joined'
    requested_sort = request.GET.get('sort', default_sort)
    requested_field = requested_sort.lstrip('-')

    if requested_field not in allowed_sort_fields:
        requested_sort = default_sort
        requested_field = default_sort.lstrip('-')

    sort_expression = allowed_sort_fields[requested_field]
    order_prefix = '-' if requested_sort.startswith('-') else ''

    order_by_fields = []
    blank_field = blank_sort_fields.get(requested_field)
    if blank_field:
        order_by_fields.append(blank_field)
    order_by_fields.append(f'{order_prefix}{sort_expression}')
    order_by_fields.append('id')

    uid = (User.objects.filter(is_active=True).select_related('uzytkownik').annotate(
        username_is_blank=Case(
            When(Q(username__isnull=True) | Q(username__exact=''), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        email_is_blank=Case(
            When(Q(email__isnull=True) | Q(email__exact=''), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        phone_is_blank=Case(
            When(Q(uzytkownik__phone__isnull=True) | Q(uzytkownik__phone__exact=''), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        last_login_is_blank=Case(
            When(last_login__isnull=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        city_is_blank=Case(
            When(Q(uzytkownik__city__isnull=True) | Q(uzytkownik__city__exact=''), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        first_name_is_blank=Case(
            When(Q(first_name__isnull=True) | Q(first_name__exact=''), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        last_name_is_blank=Case(
            When(Q(last_name__isnull=True) | Q(last_name__exact=''), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        joined_is_blank=Case(
            When(Q(uzytkownik__data_przyjecia__isnull=True), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    ).order_by(*order_by_fields))

    # Get required reputation threshold
    req_rep = required_reputation()

    # Add near-threshold data to users (only need to check if reputation <= threshold + 1)
    users_with_reputation = []
    for user in uid:
        if hasattr(user, 'uzytkownik'):
            reputation = Rate.objects.filter(kandydat_id=user.uzytkownik.id).aggregate(Sum('rate'))['rate__sum'] or 0
            user.near_threshold = reputation <= (req_rep + 1)
        else:
            user.near_threshold = False
        users_with_reputation.append(user)

    default_directions = {
        'username': 'asc',
        'email': 'asc',
        'phone': 'asc',
        'last_login': 'desc',
        'city': 'asc',
        'first_name': 'asc',
        'last_name': 'asc',
        'joined': 'desc',
    }

    sort_meta = {}
    for field in allowed_sort_fields:
        is_current = requested_field == field
        if is_current:
            current_direction = 'desc' if requested_sort.startswith('-') else 'asc'
            next_param = field if current_direction == 'desc' else f'-{field}'
        else:
            current_direction = None
            default_direction = default_directions.get(field, 'asc')
            next_param = f'-{field}' if default_direction == 'desc' else field

        sort_meta[field] = {
            'is_current': is_current,
            'direction': current_direction,
            'next_param': next_param,
        }

    return render(
        request,
        'obywatele/start.html',
        {
            'uid': users_with_reputation,  # Don't change to 'user' - it will break menu
            'sort_meta': sort_meta,
            'current_sort': requested_sort,
        }
    )


@login_required
def poczekalnia(request: HttpRequest):
    # zliczaj_obywateli(request)
    uid = User.objects.filter(is_active=False).select_related('uzytkownik')
    verified_user_ids = set(EmailAddress.objects.filter(user__in=uid, verified=True).values_list('user_id', flat=True))

    # Get the current user's profile
    try:
        citizen_profile = request.user.uzytkownik
    except Uzytkownik.DoesNotExist:
        error(request, _('Your profile does not exist. Please contact administrator.'))
        return redirect('home:index')

    candidate_profiles = {user.id: user.uzytkownik for user in uid if hasattr(user, 'uzytkownik')}
    candidate_profile_ids = [profile.id for profile in candidate_profiles.values()]
    existing_rates = {
        rate.kandydat_id: rate
        for rate in Rate.objects.filter(obywatel=citizen_profile, kandydat_id__in=candidate_profile_ids)
    }
    ratings_count_map = {
        row['kandydat_id']: row['total']
        for row in Rate.objects.filter(kandydat_id__in=candidate_profile_ids)
        .values('kandydat_id')
        .annotate(total=Count('id'))
    }

    # Get ratings from the current user for all candidates
    # Process users and add rating directly to each user object for easy access in template
    users_with_ratings = []
    for user in uid:
        candidate_profile = candidate_profiles.get(user.id)
        if not candidate_profile:
            continue

        rate = existing_rates.get(candidate_profile.id)
        if rate is None:
            rate, _ = Rate.objects.get_or_create(kandydat=candidate_profile, obywatel=citizen_profile)
            existing_rates[candidate_profile.id] = rate

        # Add rating directly to user object as a custom attribute
        user.rating = rate.rate

        # Count number of reputation votes from all citizens
        user.ratings_count = ratings_count_map.get(candidate_profile.id, 0)

        user.email_confirmed = (user.id in verified_user_ids) or bool(candidate_profile.polecajacy)
        user.form_completed = candidate_profile.onboarding_status == Uzytkownik.OnboardingStatus.FORM_COMPLETED
        users_with_ratings.append(user)

    return render(
        request,
        'obywatele/poczekalnia.html',
        {
            'uid': users_with_ratings,  # Users with ratings attached
            'population': population(),
            'acceptance': s.ACCEPTANCE,
            'delete_inactive_user_after': s.DELETE_INACTIVE_USER_AFTER,
            'required_reputation': required_reputation(),
        }
    )


def onboarding_details(request: HttpRequest):
    user = get_onboarding_user_from_request(request)
    if not user:
        error(request, _('Could not find your onboarding account.'))
        return redirect('account_signup')

    profile = user.uzytkownik

    if request.method == 'POST':
        form = OnboardingDetailsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.save()

            profile.onboarding_status = Uzytkownik.OnboardingStatus.FORM_COMPLETED
            profile.save()

            success(request, _('Your onboarding form has been saved.'))
            return redirect('obywatele:onboarding_waiting')
    else:
        form = OnboardingDetailsForm(instance=profile, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, 'obywatele/onboarding_details.html', {
        'form': form,
        'email_confirmed': EmailAddress.objects.filter(user=user, verified=True).exists(),
    })


def onboarding_waiting(request: HttpRequest):
    user = get_onboarding_user_from_request(request)
    if not user:
        error(request, _('Could not find your onboarding account.'))
        return redirect('account_signup')

    return render(request, 'obywatele/onboarding_waiting.html', {
        'email_confirmed': EmailAddress.objects.filter(user=user, verified=True).exists(),
    })


@login_required
def dodaj(request: HttpRequest):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():

            mail = user_form.cleaned_data['email']
            if User.objects.filter(email__iexact=mail).exists():
                # is_valid doesn't check if email exist
                message = _('Email already exist')
                error(request, (message))
                return redirect('obywatele:zaproponuj_osobe')

            else:
                # If everything is ok
                candidate = user_form.save()
                candidate.is_active = False
                candidate.save()

                # CANDIDATE
                candidate_profile = candidate.uzytkownik
                candidate_profile.polecajacy = request.user.username
                candidate_profile.phone = profile_form.cleaned_data['phone']
                candidate_profile.responsibilities = profile_form.cleaned_data['responsibilities']
                candidate_profile.city = profile_form.cleaned_data['city']
                candidate_profile.hobby = profile_form.cleaned_data['hobby']
                candidate_profile.skills = profile_form.cleaned_data['skills']
                candidate_profile.knowledge = profile_form.cleaned_data['knowledge']
                candidate_profile.want_to_learn = profile_form.cleaned_data['want_to_learn']
                candidate_profile.business = profile_form.cleaned_data['business']
                candidate_profile.job = profile_form.cleaned_data['job']
                candidate_profile.other = profile_form.cleaned_data['other']
                candidate_profile.save()

                # Since you proposed new person,
                # you probably also want to accept him/her
                citizen = request.user.uzytkownik
                rate = Rate()
                rate.obywatel = citizen
                rate.kandydat = candidate_profile
                rate.rate = 1
                rate.save()

                message = _('The new user has been saved')
                success(request, (message))

                log.info(f'EMAIL_DIAG trigger=new_citizen_proposed source=obywatele.views.dodaj actor_user_id={request.user.id} actor_username={request.user.username} candidate_user_id={candidate.id} candidate_username={candidate.username} subject={_("New citizen has been proposed")}')
                SendEmailToAll(_('New citizen has been proposed'), f'{request.user.username} ' + str(_('proposed new citizen\nYou can approve him/her here:')) + f' {build_site_url(f"/obywatele/poczekalnia/{candidate.id}")}')

                return redirect('obywatele:poczekalnia')
        else:
            error_messages = []

            for form in (user_form, profile_form):
                errors = form.errors.get_json_data()
                for field_errors in errors.values():
                    for err in field_errors:
                        error_messages.append(err.get('message'))

            message = error_messages[0] if error_messages else _('Please correct the highlighted errors.')
            error(request, (message))
    else:
        user_form = UserForm()
        profile_form = ProfileForm()

    return render(
        request,
        'obywatele/dodaj.html',
        {
            'user_form': user_form,
            'profile_form': profile_form,
        },
    )


@login_required
def my_profile(request: HttpRequest):
    user = request.user
    profile = request.user.uzytkownik
    
    asset_fields = [
        {'field': 'city', 'label': _('City')},
        {'field': 'phone', 'label': _('Communicator / Phone')},
        {'field': 'job', 'label': _('Job')},
        {'field': 'responsibilities', 'label': _('Responsibilities')},
        {'field': 'business', 'label': _('Business')},
        {'field': 'hobby', 'label': _('Hobby')},
        {'field': 'to_give_away', 'label': _('To give away')},
        {'field': 'to_borrow', 'label': _('To borrow')},
        {'field': 'for_sale', 'label': _('For sale')},
        {'field': 'i_need', 'label': _('I need')},
        {'field': 'want_to_learn', 'label': _('I want to learn')},
        {'field': 'skills', 'label': _('Skills')},
        {'field': 'knowledge', 'label': _('Knowledge')},
        {'field': 'gift', 'label': _('Gift')},
        {'field': 'other', 'label': _('Other')},
        {'field': 'why', 'label': _('Why do you want to join?')},
    ]
    
    notifications = [
        {
            'type': 'obywatele',
            'title': _('Citizenship'),
            'description': _('New citizens, membership requests'),
            'enabled': profile.email_notifications_obywatele,
        },
        {
            'type': 'glosowania',
            'title': _('Voting'),
            'description': _('Law proposals, voting reminders, results'),
            'enabled': profile.email_notifications_glosowania,
        },
        {
            'type': 'chat',
            'title': _('Chat'),
            'description': _('New messages in all chat rooms'),
            'enabled': profile.email_notifications_chat,
        },
        {
            'type': 'chat_participated',
            'title': _('Chat — my active discussions'),
            'description': _('New messages only in rooms where I have sent at least one message'),
            'enabled': profile.email_notifications_chat_participated,
        },
    ]
    
    profile_form = ProfileForm(initial={
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': profile.phone,
        'responsibilities': profile.responsibilities,
        'city': profile.city,
        'hobby': profile.hobby,
        'to_give_away': profile.to_give_away,
        'to_borrow': profile.to_borrow,
        'for_sale': profile.for_sale,
        'i_need': profile.i_need,
        'skills': profile.skills,
        'knowledge': profile.knowledge,
        'want_to_learn': profile.want_to_learn,
        'business': profile.business,
        'job': profile.job,
        'gift': profile.gift,
        'other': profile.other,
        'why': profile.why,
    })

    return render(request, 'obywatele/my_profile.html', {
        'profile': profile,
        'user': user,
        'population': population(),
        'required_reputation': required_reputation(),
        'asset_fields': asset_fields,
        'notifications': notifications,
        'avatar_form': AvatarForm(),
        'profile_form': profile_form,
    })


@login_required
def upload_avatar(request: HttpRequest):
    profile = request.user.uzytkownik
    if request.method == 'POST':
        form = AvatarForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
    return redirect('obywatele:my_profile')


@require_POST
def toggle_notification(request: HttpRequest):
    import json

    NOTIFICATION_FIELDS = {
        'obywatele': 'email_notifications_obywatele',
        'glosowania': 'email_notifications_glosowania',
        'chat': 'email_notifications_chat',
        'chat_participated': 'email_notifications_chat_participated',
    }

    try:
        data = json.loads(request.body)
        notification_type = request.GET.get('type')
        enabled = data.get('enabled', False)

        field_name = NOTIFICATION_FIELDS.get(notification_type)
        if not field_name:
            return JsonResponse({'success': False, 'error': 'Invalid notification type'})

        profile = request.user.uzytkownik
        setattr(profile, field_name, enabled)
        profile.save()

        return JsonResponse({'success': True})

    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def my_assets(request: HttpRequest):
    user = request.user
    profile = request.user.uzytkownik
    form = ProfileForm(request.POST, request.FILES)

    if request.method == 'POST':
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            profile.phone = form.cleaned_data['phone']
            profile.responsibilities = form.cleaned_data['responsibilities']
            profile.city = form.cleaned_data['city']
            profile.hobby = form.cleaned_data['hobby']
            profile.to_give_away = form.cleaned_data['to_give_away']
            profile.to_borrow = form.cleaned_data['to_borrow']
            profile.for_sale = form.cleaned_data['for_sale']
            profile.i_need = form.cleaned_data['i_need']
            profile.skills = form.cleaned_data['skills']
            profile.knowledge = form.cleaned_data['knowledge']
            profile.want_to_learn = form.cleaned_data['want_to_learn']
            profile.business = form.cleaned_data['business']
            profile.job = form.cleaned_data['job']
            profile.gift = form.cleaned_data['gift']
            profile.other = form.cleaned_data['other']
            profile.why = form.cleaned_data['why']
            profile.save()

            success(request, _('Changes was saved'))
            return redirect('obywatele:my_profile')
        else:  # form.is_NOT_valid():
            error(request, form.errors)
            return redirect('obywatele:my_profile')
    else:  # request.method != 'POST':
        form = ProfileForm(initial={  # pre-populate fields from database
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': profile.phone,
            'responsibilities': profile.responsibilities,
            'city': profile.city,
            'hobby': profile.hobby,
            'to_give_away': profile.to_give_away,
            'to_borrow': profile.to_borrow,
            'for_sale': profile.for_sale,
            'i_need': profile.i_need,
            'skills': profile.skills,
            'knowledge': profile.knowledge,
            'want_to_learn': profile.want_to_learn,
            'business': profile.business,
            'job': profile.job,
            'other': profile.other,
            'why': profile.why,
        })

        return render(request, 'obywatele/my_assets.html', {
            'user': user,
            'profile': profile,
            'form': form,
        })


# @login_required  # for some reason this decorator breaks urls.py
class AssetListView(SingleTableMixin, FilterView):
    # https://stackoverflow.com/questions/59094917/employeefilterset-resolved-field-emp-photo-with-exact-lookup-to-an-unrecogni

    table_class = UzytkownikTable
    model = Uzytkownik
    template_name = 'obywatele/assets.html'
    filterset_class = UzytkownikFilter

    def get_queryset(self):
        return Uzytkownik.objects.filter(uid__is_active=True)


@login_required
def obywatele_szczegoly(request: HttpRequest, pk: int):
    '''
    -[x] There has to be a table relating user and new person. This table is needed because vote for person may be withdrawn at some point. So there are 3 states:
      1. Candidate is positive
      2. Candidate is neutral (not clicked, default)
      3. Candidate is negative
    3 states are needed because:
      - this is a fact, those 3 states really exist
      - but most importantly: it should be possible to take reputation away - even if somebody did not give reputation to that person before.
    -[x] Reputation should be calculated from Rate table relating citizen and candidate.
    -[x] Counter should NOT be zeroed out if person drop below required reputation.
    -[x] New person increase population so also increase reputation requirements for existing citizens. Therefore every time new person is accepted - every other old member should have his reputation increased autmatically. And vice versa - if somebody is banned - everyone else should loose one point of reputation from banned person.
    '''
    # zliczaj_obywateli(request)  # run reputation counting because a lot can change in the meanwhile

    candidate_profile = get_object_or_404(Uzytkownik, uid_id=pk)
    candidate_user = User.objects.get(pk=pk)
    email_confirmed = is_email_confirmed_for_candidate(candidate_user, candidate_profile)
    form_completed = candidate_profile.onboarding_status == Uzytkownik.OnboardingStatus.FORM_COMPLETED
    citizen_profile = request.user.uzytkownik
    polecajacy = citizen_profile.polecajacy

    rate = Rate.objects.get_or_create(kandydat=candidate_profile, obywatel=citizen_profile)[0]

    if request.method == 'POST' and candidate_profile != citizen_profile:
        action = request.POST.get('action')
        if action == 'accept':
            rate.rate = 1
            rate.save(update_fields=['rate'])
        elif action == 'reject':
            rate.rate = -1
            rate.save(update_fields=['rate'])
        elif action == 'reset':
            rate.rate = 0
            rate.save(update_fields=['rate'])
        return redirect(request.path)

    if rate.rate == 1:
        r1 = 'positive'
    elif rate.rate == -1:
        r1 = 'negative'
    else:
        r1 = 'neutral'

    total_rate_count = Rate.objects.filter(kandydat=candidate_profile).count()

    # Previous and Next
    obj = get_object_or_404(User, pk=pk)
    # kandydaci czy obywatele? Na razie wszyscy.
    # TODO: Zrobić tak żeby przewijanie było tylko po Kandydatach albo tylko po Obywatelach
    prev = User.objects.filter(pk__lt=obj.pk, is_active=obj.is_active).order_by('-pk').first()
    next = User.objects.filter(pk__gt=obj.pk, is_active=obj.is_active).order_by('pk').first()

    return render(request, 'obywatele/szczegoly.html', {
        'b': candidate_profile,
        'd': citizen_profile,
        'wr': required_reputation(),
        'rate': r1,
        'p': polecajacy,
        'prev': prev,
        'next': next,
        'active': obj.is_active,
        'email_confirmed': email_confirmed,
        'form_completed': form_completed,
        'total_rate_count': total_rate_count,
    })


@receiver(user_signed_up)
def DeactivateNewUser(sender, **kwargs):
    user = kwargs.get('user')
    if not user:
        log.error('Missing user in DeactivateNewUser signal')
        return

    if user.is_active:
        user.is_active = False
        user.save(update_fields=['is_active'])


@receiver(email_confirmed)
def set_onboarding_email_confirmed(sender, request, email_address, **kwargs):
    user = email_address.user
    profile = user.uzytkownik

    if profile.onboarding_status == Uzytkownik.OnboardingStatus.EMAIL_ENTERED:
        profile.onboarding_status = Uzytkownik.OnboardingStatus.EMAIL_CONFIRMED
        profile.save()

    onboarding_token = signer.sign(str(user.id))
    onboarding_link = build_site_url(f'/obywatele/onboarding/?uid={user.id}&token={onboarding_token}')
    subject = f'[{HOST}] ' + _('Fill out your onboarding form')
    message = _('Your email has been confirmed. Please fill out your onboarding form here: %(link)s') % {
        'link': onboarding_link
    }

    try:
        time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
        send_mail(subject, message, s.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        log.info(f'Onboarding email sent successfully after confirmation to {user.email}; subject: {subject}')
    except Exception as e:
        log.error(f'Failed sending onboarding email after confirmation: {e}')

    # # Trigger count_citizens command after email confirmation
    # try:
    #     log.info(f"Running count_citizens command triggered by email confirmation for user {user.email}")
    #     call_command('count_citizens')
    #     log.info(f"count_citizens command completed successfully")
    # except Exception as e:
    #     log.error(f"Error running count_citizens after email confirmation: {e}", exc_info=True)


@login_required
@require_POST
def set_user_language(request: HttpRequest):
    lang = request.POST.get('language', '').strip()
    next_url = request.POST.get('next', '/')

    profile = request.user.uzytkownik
    if lang and check_for_language(lang):
        profile.language = lang
        profile.save(update_fields=['language'])
        translation.activate(lang)
        response = redirect(next_url)
        response.set_cookie(
            s.LANGUAGE_COOKIE_NAME,
            lang,
            max_age=s.LANGUAGE_COOKIE_AGE,
            path=s.LANGUAGE_COOKIE_PATH,
            domain=s.LANGUAGE_COOKIE_DOMAIN,
            secure=s.LANGUAGE_COOKIE_SECURE,
            httponly=s.LANGUAGE_COOKIE_HTTPONLY,
            samesite=s.LANGUAGE_COOKIE_SAMESITE,
        )
    elif lang == '':
        # Reset to auto-detect
        profile.language = ''
        profile.save(update_fields=['language'])
        response = redirect(next_url)
        response.delete_cookie(s.LANGUAGE_COOKIE_NAME, path=s.LANGUAGE_COOKIE_PATH)
    else:
        response = redirect(next_url)

    return response


@login_required
def citizen_czaty(request: HttpRequest, pk: int):
    from chat.models import Room, Message
    target_user = get_object_or_404(User, pk=pk)
    qs = Room.objects.filter(allowed=target_user, public=True).order_by('-last_activity')
    rows = []
    for room in qs:
        last_msg = Message.objects.filter(room=room).order_by('-time').first()
        rows.append({
            'room': room,
            'room_name': room.displayed_name(request.user),
            'last_msg': last_msg,
        })
    template = 'obywatele/_citizen_czaty_partial.html' if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else 'obywatele/citizen_czaty.html'
    return render(request, template, {
        'target_user': target_user,
        'rows': rows,
        'is_own': request.user.pk == pk,
    })


@login_required
def citizen_zadania(request: HttpRequest, pk: int):
    from tasks.models import Task
    target_user = get_object_or_404(User, pk=pk)
    tasks = (
        Task.objects
        .filter(Q(created_by=target_user) | Q(assigned_to=target_user))
        .distinct()
        .order_by('-created_at')
    )
    template = 'obywatele/_citizen_zadania_partial.html' if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else 'obywatele/citizen_zadania.html'
    return render(request, template, {
        'target_user': target_user,
        'tasks': tasks,
        'is_own': request.user.pk == pk,
    })


@login_required
def citizen_aktywnosc(request: HttpRequest, pk: int):
    import datetime
    from django.urls import reverse
    from tasks.models import Task, TaskVote, TaskEvaluation
    from glosowania.models import Argument, ZebranePodpisy, KtoJuzGlosowal

    target_user = get_object_or_404(User, pk=pk)
    target_profile = get_object_or_404(Uzytkownik, uid=target_user)
    items = []

    for t in Task.objects.filter(created_by=target_user).order_by('-created_at'):
        items.append({
            'type': 'task_created',
            'title': t.title,
            'ts': t.created_at,
            'label': _('Created task'),
            'url': reverse('tasks:detail', kwargs={'pk': t.pk}),
        })

    for t in Task.objects.filter(assigned_to=target_user).order_by('-updated_at'):
        items.append({
            'type': 'task_assigned',
            'title': t.title,
            'ts': t.updated_at,
            'label': _('Assigned task'),
            'url': reverse('tasks:detail', kwargs={'pk': t.pk}),
        })

    for tv in TaskVote.objects.filter(user=target_user).select_related('task').order_by('-updated_at'):
        items.append({
            'type': 'task_vote',
            'title': tv.task.title,
            'ts': tv.updated_at,
            'label': _('Voted on task'),
            'url': reverse('tasks:detail', kwargs={'pk': tv.task_id}),
        })

    for te in TaskEvaluation.objects.filter(user=target_user).select_related('task').order_by('-updated_at'):
        items.append({
            'type': 'task_eval',
            'title': te.task.title,
            'ts': te.updated_at,
            'label': _('Evaluated task'),
            'url': reverse('tasks:detail', kwargs={'pk': te.task_id}),
        })

    for arg in Argument.objects.filter(author=target_user).select_related('decyzja').order_by('-created_at'):
        items.append({
            'type': 'argument',
            'title': arg.decyzja.title,
            'ts': arg.created_at,
            'label': _('Added argument'),
            'url': reverse('glosowania:details', kwargs={'pk': arg.decyzja_id}),
        })

    for zp in ZebranePodpisy.objects.filter(podpis_uzytkownika=target_user).select_related('projekt'):
        if zp.projekt:
            items.append({
                'type': 'signature',
                'title': zp.projekt.title,
                'ts': None,
                'label': _('Signed proposal'),
                'url': reverse('glosowania:details', kwargs={'pk': zp.projekt_id}),
            })

    for kg in KtoJuzGlosowal.objects.filter(ktory_uzytkownik_juz_zaglosowal=target_user).select_related('projekt'):
        items.append({
            'type': 'voted',
            'title': kg.projekt.title,
            'ts': None,
            'label': _('Voted in referendum'),
            'url': reverse('glosowania:details', kwargs={'pk': kg.projekt_id}),
        })

    for ca in CitizenActivity.objects.filter(uzytkownik=target_profile).order_by('-timestamp'):
        items.append({
            'type': 'citizen',
            'title': ca.get_activity_type_display(),
            'ts': ca.timestamp,
            'label': _('Citizenship event'),
            'url': None,
        })

    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    items.sort(key=lambda x: x['ts'] or epoch, reverse=True)

    template = 'obywatele/_citizen_aktywnosc_partial.html' if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else 'obywatele/citizen_aktywnosc.html'
    return render(request, template, {
        'target_user': target_user,
        'items': items,
        'is_own': request.user.pk == pk,
    })


@login_required
def citizen_zalozono(request: HttpRequest, pk: int):
    import datetime
    from django.urls import reverse
    from tasks.models import Task
    from glosowania.models import Decyzja
    from elibrary.models import Book

    target_user = get_object_or_404(User, pk=pk)
    items = []

    for t in Task.objects.filter(created_by=target_user).order_by('-created_at'):
        items.append({
            'title': t.title,
            'ts': t.created_at,
            'label': _('Zadanie'),
            'url': reverse('tasks:detail', kwargs={'pk': t.pk}),
        })

    for d in Decyzja.objects.filter(author=target_user).order_by('-data_powstania'):
        items.append({
            'title': d.title or '—',
            'ts': datetime.datetime(d.data_powstania.year, d.data_powstania.month, d.data_powstania.day, tzinfo=datetime.timezone.utc) if d.data_powstania else None,
            'label': _('Propozycja głosowania'),
            'url': reverse('glosowania:details', kwargs={'pk': d.pk}),
        })

    for b in Book.objects.filter(uploader=target_user).order_by('-uploaded'):
        items.append({
            'title': b.title or '—',
            'ts': b.uploaded,
            'label': _('Dokument (biblioteka)'),
            'url': reverse('elibrary:book-detail', kwargs={'pk': b.pk}),
        })

    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    items.sort(key=lambda x: x['ts'] or epoch, reverse=True)

    template = 'obywatele/_citizen_zalozono_partial.html' if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else 'obywatele/_citizen_zalozono_partial.html'
    return render(request, template, {
        'target_user': target_user,
        'items': items,
        'is_own': request.user.pk == pk,
    })
