# Third party imports
from django.db.models.signals import post_save
from django.dispatch import receiver

# First party imports
from glosowania.models import Argument, KtoJuzGlosowal

# Local folder imports
from .models import OnboardingProgress


@receiver(post_save, sender=Argument)
def onboarding_step2(sender, instance, created, **kwargs):
    if created and instance.author:
        obj, _ = OnboardingProgress.objects.get_or_create(user=instance.author)
        if not obj.step2_discussed:
            obj.step2_discussed = True
            obj.save(update_fields=['step2_discussed'])


@receiver(post_save, sender=KtoJuzGlosowal)
def onboarding_step3(sender, instance, created, **kwargs):
    if created:
        obj, _ = OnboardingProgress.objects.get_or_create(
            user=instance.ktory_uzytkownik_juz_zaglosowal
        )
        if not obj.step3_voted:
            obj.step3_voted = True
            obj.save(update_fields=['step3_voted'])
