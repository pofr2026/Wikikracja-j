# Third party imports
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class PostCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))
    priority = models.PositiveIntegerField(default=10, verbose_name=_("Priority"))

    class Meta:
        ordering = ['priority', 'name']
        verbose_name = _("Post Category")
        verbose_name_plural = _("Post Categories")

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    subtitle = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("Subtitle"))
    text = models.TextField(verbose_name=_("Text"))
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("Author"))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))
    updated = models.DateTimeField(auto_now=True, verbose_name=_("Updated"))
    category = models.ForeignKey(PostCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category"))
    is_public = models.BooleanField(default=False, verbose_name=_("Public"))
    is_archived = models.BooleanField(default=False, verbose_name=_("Archived"))
    is_important = models.BooleanField(default=False, verbose_name=_("Important"))
