# Third party imports
from django import forms
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE

# Local folder imports
from .models import Post


class PostForm(forms.ModelForm):
    text = forms.CharField(widget=TinyMCE(), label=_("Text"))

    class Meta:
        model = Post
        fields = ('title', 'subtitle', 'text', 'is_public', 'is_archived', 'is_important')
