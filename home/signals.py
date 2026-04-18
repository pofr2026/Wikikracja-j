from django.db.models.signals import post_save
from django.dispatch import receiver

from glosowania.models import Argument, KtoJuzGlosowal
from chat.models import Message

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
