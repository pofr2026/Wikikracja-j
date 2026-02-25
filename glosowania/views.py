from datetime import datetime, timedelta
from glosowania.models import Decyzja, ZebranePodpisy, KtoJuzGlosowal, VoteCode, Argument
from glosowania.forms import DecyzjaForm, ArgumentForm
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.http import HttpRequest
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage
from django.conf import settings as s
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect
import logging
from django.utils import translation
import threading
import time
import random
from chat.models import Room
from zzz.utils import build_site_url, get_site_domain

log = logging.getLogger(__name__)

HOST = get_site_domain()

@login_required
def dodaj(request: HttpRequest):
    # Dodaj nową propozycję przepisu:
    # nowy = DecyzjaForm(request.POST or None)
    if request.method == 'POST':
        form = DecyzjaForm(request.POST)
        if form.is_valid():
            form = form.save(commit=False)
            form.author = request.user
            form.data_powstania = datetime.today()
            # form.ile_osob_podpisalo += 1
            form.status = 1
            form.path = _("Proposition")
            form.save()
            # signed = ZebranePodpisy.objects.create(projekt=form, podpis_uzytkownika = request.user)
            
            log.info(f"New proposal {form.id} added by {form.author}")
            message = _("New proposal has been saved.")
            messages.success(request, (message))

            SendEmail(
                _('New law proposal'),
                _('{user} added new law proposal\nYou can read it here: {url}').format(
                    user=request.user.username.capitalize(),
                    url=build_site_url(f'/glosowania/details/{form.id}')
                )
            )
            return redirect('glosowania:proposition')
        else:
            return render(request, 'glosowania/dodaj.html', {'form': form})
    else:
        form = DecyzjaForm()
    return render(request, 'glosowania/dodaj.html', {'form': form})


@login_required
def edit(request: HttpRequest, pk: int):
    decision = Decyzja.objects.get(pk=pk)

    if request.method == 'POST':
        form = DecyzjaForm(request.POST)
        if form.is_valid():
            decision.author = request.user # type: ignore
            decision.title = form.cleaned_data['title']
            decision.tresc = form.cleaned_data['tresc']
            decision.kara = form.cleaned_data['kara']
            decision.uzasadnienie = form.cleaned_data['uzasadnienie']
            decision.znosi = form.cleaned_data['znosi']
            decision.save()
            message = _("Saved.")
            messages.success(request, (message))

            SendEmail(
                _("Proposal no. {} has been modified").format(decision.id),
                _('{user} modified proposal\nYou can read new version here: {url}').format(
                    user=request.user.username.capitalize(),
                    url=build_site_url(f'/glosowania/details/{decision.id}')
                )
            )
            return redirect('glosowania:proposition')
    else:  # request.method != 'POST':
        form = DecyzjaForm(initial={
            'author': decision.author,
            'title': decision.title,
            'tresc': decision.tresc,
            'kara': decision.kara,
            'uzasadnienie': decision.uzasadnienie,
            'znosi': decision.znosi,
        })
        
    # l.info(f"Proposal {decision.id} modified by {request.user}") # Can't log that because it kicks in on form open (not on save)
    return render(request, 'glosowania/edit.html', {'form': form})


def generate_code():
    return''.join([random.SystemRandom().choice('abcdefghjkmnoprstuvwxyz23456789') for i in range(5)])


@login_required
def details(request:HttpRequest, pk: int):
    # Pokaż szczegóły przepisu

    szczegoly = get_object_or_404(Decyzja, pk=pk)

    if request.GET.get('sign'):
        nowy_projekt = Decyzja.objects.get(pk=pk)
        osoba_podpisujaca = request.user
        podpis = ZebranePodpisy(projekt=nowy_projekt, podpis_uzytkownika=osoba_podpisujaca)
        nowy_projekt.ile_osob_podpisalo += 1
        podpis.save()
        nowy_projekt.save()
        message = _('You signed this motion for a referendum.')
        messages.success(request, (message))
        return redirect('glosowania:details', pk)

    if request.GET.get('withdraw'):
        nowy_projekt = Decyzja.objects.get(pk=pk)
        osoba_podpisujaca = request.user
        podpis = ZebranePodpisy.objects.get(projekt=nowy_projekt, podpis_uzytkownika=osoba_podpisujaca)
        podpis.delete()
        nowy_projekt.ile_osob_podpisalo -= 1
        nowy_projekt.save()
        message = _('Not signed.')
        messages.success(request, (message))
        return redirect('glosowania:details', pk)

    if request.GET.get('tak'):
        nowy_projekt = Decyzja.objects.get(pk=pk)
        osoba_glosujaca = request.user
        glos = KtoJuzGlosowal(
                              projekt=nowy_projekt,
                              ktory_uzytkownik_juz_zaglosowal=osoba_glosujaca
                             )
        nowy_projekt.za += 1
        glos.save()
        nowy_projekt.save()
        
        # TODO: Kod oddanego głosu
        # - wygeneruj kod
        # - tak
        # - projekt
        # - zapisz
        # - wyswietl
        code = generate_code()
        report = VoteCode.objects.create(project=nowy_projekt, code=code, vote=True)

        message1 = str(_('Your vote has been saved. You voted Yes.'))
        messages.success(request, (message1))

        message2 = _('Your verification code is: %(code)s') % {'code': code}
        messages.error(request, (message2))

        message3 = str(_('Write down your code or create screenshot to verify it when the referendum is over. This code will be presented just once and will be not related to you.'))
        messages.info(request, (message3))

        return redirect('glosowania:details', pk)

    if request.GET.get('nie'):
        nowy_projekt = Decyzja.objects.get(pk=pk)
        osoba_glosujaca = request.user
        glos = KtoJuzGlosowal(projekt=nowy_projekt, ktory_uzytkownik_juz_zaglosowal=osoba_glosujaca)
        nowy_projekt.przeciw += 1
        glos.save()
        nowy_projekt.save()

        # TODO: Kod oddanego głosu
        # - wygeneruj kod
        # - nie
        # - projekt
        # - zapisz
        # - wyswietl
        code = generate_code()
        report = VoteCode.objects.create(project=nowy_projekt, code=code, vote=False)

        message1 = str(_('Your vote has been saved. You voted No.'))
        messages.success(request, (message1))

        message2 = _('Your verification code is: %(code)s') % {'code': code}
        messages.error(request, (message2))

        message3 = str(_('Write down your code or create screenshot to verify it when the referendum is over. This code will be presented just once and will be not related to you.'))
        messages.info(request, (message3))

        return redirect('glosowania:details', pk)

    # check if already signed
    signed = ZebranePodpisy.objects.filter(projekt=pk, podpis_uzytkownika=request.user).exists()

    # check if already voted
    voted = KtoJuzGlosowal.objects.filter(projekt=pk, ktory_uzytkownik_juz_zaglosowal=request.user).exists()

    # Report
    report = VoteCode.objects.filter(project_id=pk).order_by('vote', 'code')

    # List of voters
    voters = KtoJuzGlosowal.objects.filter(projekt=pk).select_related('ktory_uzytkownik_juz_zaglosowal').order_by('ktory_uzytkownik_juz_zaglosowal__username')

    # State dictionary
    state = {1: _('Proposition'), 2: _('Discussion'), 3: _('Referendum'), 4: _('Rejected'), 5: _('Approved'), }

    # Previous and Next
    obj = get_object_or_404(Decyzja, pk=pk)
    prev = Decyzja.objects.filter(pk__lt=obj.pk, status = szczegoly.status).order_by('-pk').first()
    next = Decyzja.objects.filter(pk__gt=obj.pk, status = szczegoly.status).order_by('pk').first()
    
    # Find associated chat room
    room_title = f"#{szczegoly.pk}:{szczegoly.title[:20]}"

    chat_room = Room.objects.filter(title=room_title).first()
    
    # Check if chat room has unseen messages
    chat_room_pulse_class = ""
    if chat_room and request.user.is_authenticated:
        if (chat_room.messages.exists() and 
            not chat_room.seen_by.filter(id=request.user.id).exists()):
            chat_room_pulse_class = "chat-room-pulse"
    
    # Query arguments for this decision
    arguments = Argument.objects.filter(decyzja=pk).select_related('author')
    
    # Custom sorting: prioritize concise arguments, then by author's argument count
    # First, get all arguments as a list to apply custom sorting
    all_arguments = list(arguments)
    
    # Count arguments per author for this decision
    from collections import Counter
    author_counts = Counter(arg.author_id for arg in all_arguments if arg.author_id)
    
    # Sort by: 1) content length (shorter first), 2) author's argument count (fewer first)
    def sort_key(arg):
        content_length = len(arg.content)
        author_arg_count = author_counts.get(arg.author_id, 0) if arg.author_id else 0
        return (content_length, author_arg_count)
    
    sorted_arguments = sorted(all_arguments, key=sort_key)
    
    # Separate into positive and negative
    positive_arguments = [arg for arg in sorted_arguments if arg.argument_type == 'FOR']
    negative_arguments = [arg for arg in sorted_arguments if arg.argument_type == 'AGAINST']
    
    # Create argument form for adding new arguments
    argument_form = ArgumentForm()
    
    return render(request, 'glosowania/szczegoly.html', {'id': szczegoly,
                                                         'signed': signed,
                                                         'voted': voted,
                                                         'report': report,
                                                         'voters': voters,
                                                         'current_user': request.user,
                                                         'state': state[szczegoly.status],
                                                         'data_referendum_stop': szczegoly.data_referendum_stop,
                                                         'prev': prev,
                                                         'next': next,
                                                         'chat_room': chat_room,
                                                         'chat_room_pulse_class': chat_room_pulse_class,
                                                         'positive_arguments': positive_arguments,
                                                         'negative_arguments': negative_arguments,
                                                         'argument_form': argument_form,
                                                         })


@login_required
def add_argument(request: HttpRequest, pk: int):
    """Add a new argument to decision pk"""
    decyzja = get_object_or_404(Decyzja, pk=pk)
    
    # Block adding arguments after voting has ended (status 4=Rejected or 5=Approved)
    if decyzja.status in [4, 5]:
        messages.error(request, _("Arguments cannot be added after voting has ended."))
        return redirect('glosowania:details', pk)
    
    if request.method == 'POST':
        form = ArgumentForm(request.POST)
        if form.is_valid():
            argument = form.save(commit=False)
            argument.decyzja = decyzja
            argument.author = request.user
            argument.save()
            
            arg_type = argument.get_argument_type_display()
            message = _("Your {type} argument has been added.").format(type=arg_type.lower())
            messages.success(request, message)
            
            log.info(f"User {request.user} added {argument.argument_type} argument to decision #{pk}")
        else:
            messages.error(request, _("There was an error with your argument. Please try again."))
    
    return redirect('glosowania:details', pk)


@login_required
def edit_argument(request: HttpRequest, argument_id: int):
    """Edit an existing argument (only by its author)"""
    argument = get_object_or_404(Argument, pk=argument_id)
    
    # Check if user is the author
    if argument.author != request.user:
        messages.error(request, _("You can only edit your own arguments."))
        return redirect('glosowania:details', argument.decyzja.pk)
    
    # Block editing after voting has ended (status 4=Rejected or 5=Approved)
    if argument.decyzja.status in [4, 5]:
        messages.error(request, _("Arguments cannot be edited after voting has ended."))
        return redirect('glosowania:details', argument.decyzja.pk)
    
    if request.method == 'POST':
        form = ArgumentForm(request.POST, instance=argument)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your argument has been updated."))
            log.info(f"User {request.user} edited argument #{argument_id}")
            return redirect('glosowania:details', argument.decyzja.pk)
    else:
        form = ArgumentForm(instance=argument)
    
    return render(request, 'glosowania/edit_argument.html', {
        'form': form,
        'argument': argument,
        'decyzja': argument.decyzja,
    })


@login_required
def delete_argument(request: HttpRequest, argument_id: int):
    """Delete an argument (only by its author)"""
    argument = get_object_or_404(Argument, pk=argument_id)
    decyzja_pk = argument.decyzja.pk
    
    # Check if user is the author
    if argument.author != request.user:
        messages.error(request, _("You can only delete your own arguments."))
        return redirect('glosowania:details', decyzja_pk)
    
    # Block deletion after voting has ended (status 4=Rejected or 5=Approved)
    if argument.decyzja.status in [4, 5]:
        messages.error(request, _("Arguments cannot be deleted after voting has ended."))
        return redirect('glosowania:details', decyzja_pk)
    
    if request.method == 'POST':
        log.info(f"User {request.user} deleted argument #{argument_id} from decision #{decyzja_pk}")
        argument.delete()
        messages.success(request, _("Your argument has been deleted."))
        return redirect('glosowania:details', decyzja_pk)
    
    return render(request, 'glosowania/delete_argument.html', {
        'argument': argument,
        'decyzja': argument.decyzja,
    })


def SendEmail(subject: str, message: str):
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

# proposition = 1
# discussion = 2
# referendum = 3
# rejected = 4
# approved = 5


@login_required
def parameters(request: HttpRequest):
    return render(request, 'glosowania/parameters.html', {
        'signatures': s.WYMAGANYCH_PODPISOW,
        'signatures_span': timedelta(days=s.CZAS_NA_ZEBRANIE_PODPISOW).days,
        'queue_span': timedelta(days=s.DYSKUSJA).days,
        'referendum_span': timedelta(days=s.CZAS_TRWANIA_REFERENDUM).days,
    })


@login_required
def rejected(request: HttpRequest):
    votings = Decyzja.objects.filter(status=4).order_by('id')
    return render(request, 'glosowania/rejected.html', {'votings': votings})


@login_required
def proposition(request: HttpRequest):
    votings = Decyzja.objects.filter(status=1).order_by('data_referendum_start')
    
    # Add chat room info for each voting
    for voting in votings:
        room_title = f"#{voting.pk}:{voting.title[:20]}"
        chat_room = Room.objects.filter(title=room_title).first()
        voting.chat_room = chat_room
        
        # Check for unseen messages
        if chat_room and request.user.is_authenticated:
            if (chat_room.messages.exists() and 
                not chat_room.seen_by.filter(id=request.user.id).exists()):
                voting.chat_room_pulse_class = "chat-room-pulse"
            else:
                voting.chat_room_pulse_class = ""
        else:
            voting.chat_room_pulse_class = ""
    
    return render(request, 'glosowania/proposition.html', {'votings': votings})


@login_required
def discussion(request: HttpRequest):
    votings = Decyzja.objects.filter(status=2).order_by('data_referendum_start')
    
    # Add chat room info for each voting
    for voting in votings:
        room_title = f"#{voting.pk}:{voting.title[:20]}"
        chat_room = Room.objects.filter(title=room_title).first()
        voting.chat_room = chat_room
        
        # Check for unseen messages
        if chat_room and request.user.is_authenticated:
            if (chat_room.messages.exists() and 
                not chat_room.seen_by.filter(id=request.user.id).exists()):
                voting.chat_room_pulse_class = "chat-room-pulse"
            else:
                voting.chat_room_pulse_class = ""
        else:
            voting.chat_room_pulse_class = ""
    
    return render(request, 'glosowania/discussion.html', {'votings': votings})


@login_required
def referendum(request: HttpRequest):
    votings = Decyzja.objects.filter(status=3).order_by('data_referendum_start')
    
    # Add chat room info for each voting
    for voting in votings:
        room_title = f"#{voting.pk}:{voting.title[:20]}"
        chat_room = Room.objects.filter(title=room_title).first()
        voting.chat_room = chat_room
        
        # Check for unseen messages
        if chat_room and request.user.is_authenticated:
            if (chat_room.messages.exists() and 
                not chat_room.seen_by.filter(id=request.user.id).exists()):
                voting.chat_room_pulse_class = "chat-room-pulse"
            else:
                voting.chat_room_pulse_class = ""
        else:
            voting.chat_room_pulse_class = ""
    
    return render(request, 'glosowania/referendum.html', {'votings': votings})


@login_required
def approved(request: HttpRequest):
    votings = Decyzja.objects.filter(status=5).order_by('data_referendum_start')
    return render(request, 'glosowania/approved.html', {'votings': votings})
