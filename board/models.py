from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Post(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    subtitle = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("Subtitle"))
    text = models.TextField(verbose_name=_("Text"))
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("Author"))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))
    updated = models.DateTimeField(auto_now=True, verbose_name=_("Updated"))
    is_public = models.BooleanField(default=False, verbose_name=_("Public"))
    is_archived = models.BooleanField(default=False, verbose_name=_("Archived"))
    is_important = models.BooleanField(default=False, verbose_name=_("Important"))
