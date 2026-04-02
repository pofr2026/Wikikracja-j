# Standard library imports
import logging
import threading
import time

# Third party imports
from allauth.account.forms import SignupForm
from captcha.fields import CaptchaField
from django import forms
from django.conf import settings as s
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.http import HttpRequest
from django.utils import translation
from django.utils.translation import gettext_lazy as _

# First party imports
from obywatele.models import Uzytkownik
from zzz.utils import build_site_url, get_site_domain

log = logging.getLogger(__name__)


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


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
    first_name = forms.CharField(max_length=150, label=_('First name'), required=True)
    last_name = forms.CharField(max_length=150, label=_('Last name'), required=True)

    class Meta:
        model = Uzytkownik
        fields = ('phone', 'responsibilities', 'city', 'hobby', 'to_give_away', 'to_borrow', 'for_sale', 'i_need', 'skills', 'knowledge', 'want_to_learn', 'business', 'job', 'gift', 'other', 'why')

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['phone'].label = _('Communicator or Phone number')
        self.fields['phone'].required = True
        self.fields['city'].required = True
        self.fields['job'].required = True

        self.fields['first_name'].error_messages['required'] = _('First name is required.')
        self.fields['last_name'].error_messages['required'] = _('Last name is required.')
        self.fields['phone'].error_messages['required'] = _('Phone number is required.')
        self.fields['city'].error_messages['required'] = _('City is required.')
        self.fields['job'].error_messages['required'] = _('Job is required.')


class OnboardingDetailsForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label=_('First name'), required=True)
    last_name = forms.CharField(max_length=150, label=_('Last name'), required=True)

    class Meta:
        model = Uzytkownik
        fields = ('why', 'phone', 'city', 'job', 'hobby', 'business', 'skills', 'knowledge')

    def __init__(self, *args, **kwargs):
        super(OnboardingDetailsForm, self).__init__(*args, **kwargs)
        self.fields['phone'].label = _('Communicator or Phone number')
        self.fields['phone'].required = True
        self.fields['city'].required = True
        self.fields['job'].required = True

        self.fields['first_name'].error_messages['required'] = _('First name is required.')
        self.fields['last_name'].error_messages['required'] = _('Last name is required.')
        self.fields['phone'].error_messages['required'] = _('Phone number is required.')
        self.fields['city'].error_messages['required'] = _('City is required.')
        self.fields['job'].error_messages['required'] = _('Job is required.')


class CustomSignupForm(SignupForm):
    email = forms.CharField(max_length=100, label='Email', required=True)
    captcha = CaptchaField()

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.fields.pop('password1')

    def clean_email(self):
        email = self.cleaned_data['email']
        existing_user = User.objects.filter(email__iexact=email).first()

        if existing_user:
            if not existing_user.is_active:
                raise forms.ValidationError(_('Your candidacy is still in the queue. Please wait for verification.'))
            else:
                raise forms.ValidationError(_('An account with this email address already exists.'))

        return email

    def save(self, request: HttpRequest):
        user = super(CustomSignupForm, self).save(request)
        user.email = self.cleaned_data['email']
        if not User.objects.filter(username=user.username).exists():
            user.set_unusable_password()

        try:
            user.save()
        except Exception as _e:
            # Handle unique constraint violation
            # Delete this user if a duplicate with the same email already exists
            existing = User.objects.filter(email__iexact=user.email).exclude(id=user.id).first()
            if existing:
                user.delete()
                user = existing
            else:
                raise

        profile = user.uzytkownik
        profile.onboarding_status = Uzytkownik.OnboardingStatus.EMAIL_ENTERED
        profile.save()

        request.session['onboarding_user_id'] = user.id
        request.session.modified = True

        log.info(f'EMAIL_DIAG trigger=new_person_requested_membership source=obywatele.forms.CustomSignupForm.save user_id={user.id} email={user.email} username={user.username} subject={_("New person requested membership")}')
        SendEmailToAll(_('New person requested membership'),
                       _('User %(username)s just requested membership') % {
                           'username': user.username
                       } + '\n' + build_site_url('/obywatele/poczekalnia/'))
        return user


def SendEmailToAll(subject, message):
    # bcc: all active users
    # subject: Custom
    # message: Custom
    translation.activate(s.LANGUAGE_CODE)
    HOST = get_site_domain()

    info_url = "https://wikikracja.pl/powiadomienia-email/"
    email_footer = _("Why you received this email? Here is explanation: {url}").format(url=info_url)

    recipients = list(User.objects.filter(is_active=True).values_list('email', flat=True))
    email_message = EmailMessage(
        from_email=str(s.DEFAULT_FROM_EMAIL),
        bcc=recipients,
        subject=f'[{HOST}] {subject}',
        body=f"{message}\n\n{email_footer}",
    )
    log.info(f'Sending email to {len(recipients)} recipients; subject: {subject}')

    def _send_with_delay():
        try:
            time.sleep(s.EMAIL_SEND_DELAY_SECONDS)
            email_message.send(fail_silently=False)
            log.info(f'Email sent successfully; subject: {subject}')
        except Exception as e:
            log.error(f'Failed to send email; subject: {subject}; error: {e}', exc_info=True)

    t = threading.Thread(target=_send_with_delay)
    t.setDaemon(True)
    t.start()
