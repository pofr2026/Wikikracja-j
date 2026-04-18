from django.db import models
from django.utils.translation import gettext_lazy as _


class SiteSettings(models.Model):
    onboarding_category = models.ForeignKey(
        'board.PostCategory',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('Onboarding category'),
        help_text=_('Posts from this category can be marked as required reading'),
    )
    onboarding_posts = models.ManyToManyField(
        'board.Post',
        blank=True,
        verbose_name=_('Onboarding documents'),
        help_text=_('Posts the user must read during onboarding'),
    )

    class Meta:
        verbose_name = _('Site settings')

    def __str__(self):
        return 'Site Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
