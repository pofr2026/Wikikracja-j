from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from board.models import Post
from chat.models import Message
from elibrary.models import Book
from events.models import Event
from glosowania.models import Argument, Decyzja, KtoJuzGlosowal
from obywatele.models import CitizenActivity
from tasks.models import Task

from .models import OnboardingProgress


@receiver(post_save, sender=Argument)
def onboarding_step_argued(sender, instance, created, **kwargs):
    if created and instance.author:
        obj, _ = OnboardingProgress.objects.get_or_create(user=instance.author)
        if not obj.step_argued:
            obj.step_argued = True
            obj.save(update_fields=['step_argued'])


@receiver(post_save, sender=Message)
def onboarding_step_chatted(sender, instance, created, **kwargs):
    if created and instance.sender:
        obj, _ = OnboardingProgress.objects.get_or_create(user=instance.sender)
        if not obj.step_chatted:
            obj.step_chatted = True
            obj.save(update_fields=['step_chatted'])


@receiver(post_save, sender=KtoJuzGlosowal)
def onboarding_step_voted(sender, instance, created, **kwargs):
    if created:
        obj, _ = OnboardingProgress.objects.get_or_create(
            user=instance.ktory_uzytkownik_juz_zaglosowal
        )
        if not obj.step_voted:
            obj.step_voted = True
            obj.save(update_fields=['step_voted'])


# Feed cache invalidation — clear global feed cache when any feed-related model changes
_FEED_SIGNAL_SENDERS = (Post, Task, Book, Event, Decyzja, CitizenActivity, Message)

for _sender in _FEED_SIGNAL_SENDERS:
    @receiver(post_save, sender=_sender, weak=False)
    @receiver(post_delete, sender=_sender, weak=False)
    def _invalidate_feed_cache(sender, **kwargs):
        from .views import invalidate_feed_cache
        invalidate_feed_cache()


# Elibrary cache invalidation
@receiver(post_save, sender=Post)
@receiver(post_delete, sender=Post)
@receiver(post_save, sender=Book)
@receiver(post_delete, sender=Book)
def _invalidate_elibrary_cache(sender, **kwargs):
    from elibrary.views import invalidate_elibrary_cache
    invalidate_elibrary_cache()
