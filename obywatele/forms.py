from django import forms
from django.http import HttpRequest
from obywatele.models import Uzytkownik
from django.contrib.auth.models import User
from allauth.account.forms import SignupForm
from django.utils.translation import gettext_lazy as _
from django.utils import translation
from django.conf import settings as s
from django.core.mail import EmailMessage
import threading
import time
from captcha.fields import CaptchaField
from zzz.utils import build_site_url, get_site_domain

import logging
log = logging.getLogger(__name__)
logging.basicConfig(filename='/var/log/wiki.log', datefmt='%d-%b-%y %H:%M:%S', format='%(asctime)s %(levelname)s %(funcName)s() %(message)s', level=logging.INFO)

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class NameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(NameChangeForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        first_name = self.cleaned_data["first_name"]
        last_name = self.cleaned_data["last_name"]
        self.user.first_name = first_name
        self.user.last_name = last_name
        if commit:
            self.user.save()
        return self.user


class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username',)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UsernameChangeForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        username = self.cleaned_data["username"]
        self.user.username = username
        if commit:
            self.user.save()
        return self.user


class EmailChangeForm(forms.Form):
    """
    A form that lets a user change set their email while checking for a change in the 
    e-mail.
    """
    error_messages = {
        'email_mismatch': _("The two email addresses fields didn't match."),
        'not_changed': _("The email address is the same as the one already defined."),
    }

    new_email1 = forms.EmailField(
        label=_("New email address"),
        widget=forms.EmailInput,
    )

    new_email2 = forms.EmailField(
        label=_("New email address confirmation"),
        widget=forms.EmailInput,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(EmailChangeForm, self).__init__(*args, **kwargs)

    def clean_new_email1(self):
        old_email = self.user.email
        new_email1 = self.cleaned_data.get('new_email1')
        if new_email1 and old_email:
            if new_email1 == old_email:
                raise forms.ValidationError(
                    self.error_messages['not_changed'],
                    code='not_changed',
                )
        return new_email1

    def clean_new_email2(self):
        new_email1 = self.cleaned_data.get('new_email1')
        new_email2 = self.cleaned_data.get('new_email2')
        if new_email1 and new_email2:
            if new_email1 != new_email2:
                raise forms.ValidationError(
                    self.error_messages['email_mismatch'],
                    code='email_mismatch',
                )
        return new_email2

    def save(self, commit=True):
        email = self.cleaned_data["new_email1"]
        self.user.email = email
        if commit:
            self.user.save()
        return self.user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Uzytkownik
        fields = ('phone', 'responsibilities', 'city', 'hobby',
                  'to_give_away', 'to_borrow', 'for_sale', 'i_need',
                  'skills', 'knowledge', 'want_to_learn', 'business',
                  'job', 'gift', 'other', 'why')


class OnboardingDetailsForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label=_('First name'), required=False)
    last_name = forms.CharField(max_length=150, label=_('Last name'), required=False)

    class Meta:
        model = Uzytkownik
        fields = ('why', 'phone', 'city', 'job', 'hobby', 'business', 'skills', 'knowledge')


class CustomSignupForm(SignupForm):
    email = forms.CharField(max_length=100, label='Email', required=True)
    captcha = CaptchaField()

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.fields.pop('password1')

    def clean_email(self):
        email = self.cleaned_data['email']
        existing_user = User.objects.filter(email__iexact=email).first()

        if existing_user and not existing_user.is_active:
            raise forms.ValidationError(
                _('Your candidacy is still in the queue. Please wait for verification.')
            )

        return email
 
    def save(self, request: HttpRequest):
        user = super(CustomSignupForm, self).save(request)
        user.email = self.cleaned_data['email']
        if not User.objects.filter(username=user.username).exists():
            user.set_unusable_password()
        user.save()

        profile = user.uzytkownik
        profile.onboarding_status = Uzytkownik.OnboardingStatus.EMAIL_ENTERED
        profile.save()

        request.session['onboarding_user_id'] = user.id
        request.session.modified = True
    
        HOST = get_site_domain()
        SendEmailToAll(
            _('New person requested membership'),
            _('User %(username)s just requested membership') % {'username': user.username} + '\n' + build_site_url('/obywatele/poczekalnia/')
        )
        return user


def SendEmailToAll(subject, message):
    # bcc: all active users
    # subject: Custom
    # message: Custom
    translation.activate(s.LANGUAGE_CODE)
    HOST = get_site_domain()

    info_url = "https://wikikracja.pl/powiadomienia-email/"
    email_footer = _("Why you received this email? Here is explanation: {url}").format(url=info_url)

    email_message = EmailMessage(
        from_email=str(s.DEFAULT_FROM_EMAIL),
        bcc = list(User.objects.filter(is_active=True).values_list('email', flat=True)),
        subject=f'[{HOST}] {subject}',
        body=f"{message}\n\n{email_footer}",
        )
    log.info(f'subject: {subject} message: {message}')
    
    def _send_with_delay():
        time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
        email_message.send(fail_silently=False)

    t = threading.Thread(target=_send_with_delay)
    t.setDaemon(True)
    t.start()



'''
class SignupForm(forms.ModelForm):
    # https://stackoverflow.com/questions/35580077/django-allauth-signup-without-password
    class Meta:
        model = User
        fields = ('username', 'email')
        exclude = ('password',)

    username = forms.CharField(label=_("username"))
    email = forms.CharField(label=_("email"))

    def signup(self, request, user):
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.set_unusable_password()
        user.save()
'''

'''
from django.contrib.auth.forms import AuthenticationForm
class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", max_length=30,
                               widget=forms.TextInput(attrs={
                                   'class': 'form-control', 'name': 'username'
                                   }))
    password = forms.CharField(label="Password", max_length=30,
                               widget=forms.TextInput(attrs={
                                   'class': 'form-control', 'name': 'password'
                                   }))
'''
