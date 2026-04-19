# Third party imports
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE

# Local folder imports
from .models import Post, PostCategory


class PostCategoryForm(forms.ModelForm):
    class Meta:
        model = PostCategory
        fields = ('name', 'priority')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', _('Save'), css_class='btn-primary'))


class PostForm(forms.ModelForm):
    text = forms.CharField(widget=TinyMCE(), label=_("Text"))

    class Meta:
        model = Post
        fields = ('title', 'subtitle', 'category', 'text', 'is_public', 'is_archived', 'is_important')
