from django.conf import settings as s
from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.messages import success, error
from django.db.models import Sum, Case, When, Value, IntegerField, Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta as td
from django.utils.translation import gettext_lazy as _
from random import choice
from string import ascii_letters, digits
import logging
from obywatele.forms import UserForm, ProfileForm, EmailChangeForm, NameChangeForm, UsernameChangeForm, OnboardingDetailsForm
from obywatele.models import Uzytkownik, Rate
from django.utils import translation
from django.core.mail import EmailMessage
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
import threading
import time
from obywatele.tables import UzytkownikTable
from obywatele.filters import UzytkownikFilter
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
# from django_tables2.export import TableExport
from allauth.account.signals import user_signed_up, email_confirmed
from allauth.account.models import EmailAddress
from django.dispatch import receiver
from chat import signals
from django.contrib.auth.models import Group, Permission
from zzz.utils import build_site_url, get_site_domain

HOST = get_site_domain()

log = logging.getLogger(__name__)
# logging.basicConfig(filename='/var/log/wiki.log', datefmt='%d-%b-%y %H:%M:%S', format='%(asctime)s %(levelname)s %(funcName)s() %(message)s', level=logging.INFO)

signer = TimestampSigner()


def is_email_confirmed_for_candidate(user: User, profile: Uzytkownik) -> bool:
    if profile.polecajacy:
        return True
    return EmailAddress.objects.filter(user=user, verified=True).exists()


def get_onboarding_user_from_request(request: HttpRequest):
    onboarding_user_id = request.session.get('onboarding_user_id')

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

    return User.objects.filter(pk=onboarding_user_id, is_active=False).first()


def population():
    try:
        population = User.objects.filter(is_active=True).count()
        return population
    except:
        l.error(f"Population zero, I don't know what to do.")


def required_reputation():
    if population() <= s.ACCEPTANCE*2:
        return population()-s.ACCEPTANCE
    if population() > s.ACCEPTANCE*2:
        return s.ACCEPTANCE
    '''
    Liczba Próg
    L    L-P
    1 -> 1-3=-2
    2 -> 2-3=-1
    3 -> 3-3=+0
    4 -> 4-3=+1
    5 -> 5-3=+2
    6 -> 6-3=+3
    7 -> 7-3=+3
    8 -> 8-3=+3
    '''


@login_required
def parameters(request: HttpRequest):
    return render(request, 'obywatele/parameters.html', {
        'population': population(),
        'acceptance': s.ACCEPTANCE,
        'delete_inactive_user_after': s.DELETE_INACTIVE_USER_AFTER,
    })


@login_required() 
def change_email(request: HttpRequest):
    form = EmailChangeForm(request.user)
    if request.method=='POST':
        form = EmailChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            message = _("Your new email has been saved.")
            success(request, (message))
            return redirect('obywatele:my_profile')
        else:
            message = form.errors
            error(request, (message))
            return redirect('obywatele:my_profile')
    else:
        return render(request, 'obywatele/change_email.html', {'form':form})


@login_required() 
def change_name(request: HttpRequest):
    form = NameChangeForm(request.POST)
    if request.method=='POST':
        # form = NameChangeForm(request.POST, request.user)
        form = NameChangeForm(request.user, request.POST)
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
        return render(request, 'obywatele/change_name.html', {'form':form})


@login_required() 
def change_username(request: HttpRequest):
    form = UsernameChangeForm(request.POST)
    if request.method=='POST':
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
        return render(request, 'obywatele/change_username.html', {'form':form})


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

    uid = (
        User.objects.filter(is_active=True)
        .select_related('uzytkownik')
        .annotate(
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
        )
        .order_by(*order_by_fields)
    )

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

    return render(request, 'obywatele/start.html', {
        'uid': uid,  # Don't change to 'user' - it will break menu
        'sort_meta': sort_meta,
        'current_sort': requested_sort,
        })


@login_required
def poczekalnia(request: HttpRequest):
    # zliczaj_obywateli(request)
    uid = User.objects.filter(is_active=False)
    verified_user_ids = set(
        EmailAddress.objects.filter(user__in=uid, verified=True).values_list('user_id', flat=True)
    )
    
    # Get the current user's profile
    citizen_profile = Uzytkownik.objects.get(uid=request.user)
    
    # Get ratings from the current user for all candidates
    # Process users and add rating directly to each user object for easy access in template
    users_with_ratings = []
    for user in uid:
        candidate_profile = Uzytkownik.objects.get(uid=user)
        rate, created = Rate.objects.get_or_create(kandydat=candidate_profile, obywatel=citizen_profile)
        # Add rating directly to user object as a custom attribute
        user.rating = rate.rate
        user.email_confirmed = (user.id in verified_user_ids) or bool(candidate_profile.polecajacy)
        user.form_completed = candidate_profile.onboarding_status == Uzytkownik.OnboardingStatus.FORM_COMPLETED
        users_with_ratings.append(user)
        
    return render(request, 'obywatele/poczekalnia.html', {
        'uid': users_with_ratings,  # Users with ratings attached
        'population': population(),
        'acceptance': s.ACCEPTANCE,
        'delete_inactive_user_after': s.DELETE_INACTIVE_USER_AFTER,
        'required_reputation': required_reputation(),
        })


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
        form = OnboardingDetailsForm(
            instance=profile,
            initial={
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        )

    return render(request, 'obywatele/onboarding_details.html', {
        'form': form,
        'email_confirmed': EmailAddress.objects.filter(user=user, verified=True).exists(),
    })


def onboarding_waiting(request: HttpRequest):
    user = get_onboarding_user_from_request(request)
    if not user:
        error(request, _('Could not find your onboarding account.'))
        return redirect('account_signup')

    profile = user.uzytkownik
    return render(request, 'obywatele/onboarding_waiting.html', {
        'email_confirmed': EmailAddress.objects.filter(user=user, verified=True).exists(),
    })


@login_required
def dodaj(request: HttpRequest):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            
            # USER
            nick = user_form.cleaned_data['username']
            first_name = user_form.cleaned_data['first_name']
            last_name = user_form.cleaned_data['last_name']

            mail = user_form.cleaned_data['email']
            if User.objects.filter(email=mail).exists():
                # is_valid doesn't check if email exist
                message = _('Email already exist')
                error(request, (message))
                return redirect('obywatele:zaproponuj_osobe')

            else:
                # If everything is ok
                user_form.save()
                candidate = User.objects.get(username=nick)
                candidate.is_active = False
                candidate.save()

                # CANDIDATE
                candidate_profile = Uzytkownik.objects.get(id=candidate.id)
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
                citizen = Uzytkownik.objects.get(pk=request.user.id)
                rate = Rate()
                rate.obywatel = citizen
                rate.kandydat = candidate_profile
                rate.rate = 1
                rate.save()

                message = _('The new user has been saved')
                success(request, (message))

                SendEmailToAll(
                          _('New citizen has been proposed'),
                          f'{request.user.username} ' + str(_('proposed new citizen\nYou can approve him/her here:')) + f' {build_site_url(f"/obywatele/poczekalnia/{candidate_profile.id}")}'
                )

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
    pk=request.user.id
    profile = Uzytkownik.objects.get(pk=pk)
    user = User.objects.get(pk=pk)
    return render(request, 'obywatele/my_profile.html', {'profile': profile,
                                                         'user': user,
                                                         'population': population(),
                                                         'required_reputation': required_reputation(),})


@login_required
def my_assets(request: HttpRequest):
    pk=request.user.id
    profile = Uzytkownik.objects.get(pk=pk)
    user = User.objects.get(pk=pk)
    form = ProfileForm(request.POST, request.FILES)

    if request.method == 'POST':
        if form.is_valid():
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
            profile.save()

            return render(
                request,
                'obywatele/my_profile.html',
                {
                    'message': _('Changes was saved'),
                    'profile': profile,
                    'required_reputation': required_reputation(),
                }
            )
        else:  # form.is_NOT_valid():
            message = form.errors
            error(request, (message))

            return render(
                request,
                'obywatele/my_profile.html',
                {
                    'message': _('Form is not valid!'),
                    'profile': profile,
                    'required_reputation': required_reputation(),
                }
            )
    else:  # request.method != 'POST':
        form = ProfileForm(initial={  # pre-populate fields from database
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
            }
        )

        return render(
            request,
            'obywatele/my_assets.html',
            {
                'user': user,
                'profile': profile,
                'form': form,
            }
        )


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

    candidate_profile = get_object_or_404(Uzytkownik, pk=pk)
    candidate_user = User.objects.get(pk=pk)
    email_confirmed = is_email_confirmed_for_candidate(candidate_user, candidate_profile)
    form_completed = candidate_profile.onboarding_status == Uzytkownik.OnboardingStatus.FORM_COMPLETED
    citizen_profile = Uzytkownik.objects.get(pk=request.user.id)
    citizen_reputation = citizen_profile.reputation
    polecajacy = citizen_profile.polecajacy

    rate = Rate.objects.get_or_create(kandydat=candidate_profile, obywatel=citizen_profile)[0]

    if rate.rate == 1:
        r1 = _('positive')
    if request.GET.get('tak'):
        rate.rate = 1
        rate.save()
        return redirect('obywatele:obywatele_szczegoly', pk)

    if rate.rate == -1:
        r1 = _('negative')
    if request.GET.get('nie'):
        rate.rate = -1
        rate.save()
        return redirect('obywatele:obywatele_szczegoly', pk)

    if rate.rate == 0:
        r1 = _('neutral')
    if request.GET.get('reset'):
        rate.rate = 0
        rate.save()
        return redirect('obywatele:obywatele_szczegoly', pk)

    # Previous and Next
    obj = get_object_or_404(User, pk=pk)
    # kandydaci czy obywatele? Na razie wszyscy.
    # TODO: Zrobić tak żeby przewijanie było tylko po Kandydatach albo tylko po Obywatelach
    prev = User.objects.filter(pk__lt=obj.pk, is_active=obj.is_active).order_by('-pk').first()
    next = User.objects.filter(pk__gt=obj.pk, is_active=obj.is_active).order_by('pk').first()
  
    return render(
        request,
        'obywatele/szczegoly.html',
        {
            'b': candidate_profile,
            'd': citizen_profile,
            'tr': citizen_reputation,
            'wr': required_reputation(),
            'rate': r1,
            'p': polecajacy,
            'prev': prev,
            'next': next,
            'active': obj.is_active,
            'email_confirmed': email_confirmed,
            'form_completed': form_completed,
        })


def zliczaj_obywateli(request: HttpRequest):  # TODO: Remove this function if everything works
    """
    View that runs the count_citizens management command to process user reputation
    and activate/deactivate users based on reputation thresholds.
    
    The logic has been moved to a management command for better maintainability
    and to allow scheduling via cron.
    """
    from django.core.management import call_command
    from io import StringIO
    
    # Capture command output
    stdout = StringIO()
    stderr = StringIO()
    
    try:
        # Run the management command with the current request host for context
        call_command('count_citizens', stdout=stdout, stderr=stderr)
        if stdout.getvalue():
            l.info(stdout.getvalue())
        if stderr.getvalue():
            l.error(stderr.getvalue())
    except Exception as e:
        l.error(f"Error running count_citizens command: {str(e)}")
    
    return redirect('obywatele:poczekalnia')


@login_required
def change_password(request: HttpRequest):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            success(request,
                             'Your password was successfully updated!')
            return redirect('change_password')
        else:
            error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'obywatele/change_password.html', {'form': form})


def password_generator(size=8, chars=ascii_letters + digits):
    return ''.join(choice(chars) for i in range(size))


def SendEmailToAll(subject, message):
    # bcc: all active users
    # subject: Custom
    # message: Custom
    translation.activate(s.LANGUAGE_CODE)

    info_url = "https://wikikracja.pl/powiadomienia-email/"
    email_footer = _("Why you received this email? Here is explanation: {url}").format(url=info_url)

    email_message = EmailMessage(
        from_email=str(s.DEFAULT_FROM_EMAIL),
        bcc = list(User.objects.filter(is_active=True).values_list('email', flat=True)),
        subject=f'[{HOST}] {subject}',
        body=message + "\n\n" + email_footer,
        )
    # l.info(f'subject: {subject} \n message: {message}')
    
    def _send_with_delay():
        time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
        email_message.send(fail_silently=False)

    t = threading.Thread(target=_send_with_delay)
    t.setDaemon(True)
    t.start()


@receiver(user_signed_up)
def DeactivateNewUser(sender, **kwargs):
    u = User.objects.get(username=kwargs['user'])
    u.is_active=False
    u.save()


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
    message = _(
        'Your email has been confirmed. Please fill out your onboarding form here: %(link)s'
    ) % {'link': onboarding_link}

    try:
        time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
        send_mail(subject, message, s.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception as e:
        l.error(f'Failed sending onboarding email after confirmation: {e}')
