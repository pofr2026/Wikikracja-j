# Third party imports
from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

# First party imports
from elibrary.models import Book


class UpdateBookForm(forms.ModelForm):
    title = forms.CharField(max_length=200, label=_('Title'))
    author = forms.CharField(max_length=200, label=_('Author'), required=False)
    abstract = forms.CharField(widget=forms.Textarea, required=False, label=_('Abstract'), max_length=5000)
    cover = forms.ImageField(required=False, label=_('Cover'))
    # tag = forms.CharField(required=False)
    file_epub = forms.FileField(required=False, label=_('File epub'), widget=forms.FileInput(attrs={
        'accept': '.epub'
    }), validators=[FileExtensionValidator(['epub'])])
    file_mobi = forms.FileField(required=False, label=_('File mobi'), widget=forms.FileInput(attrs={
        'accept': '.mobi'
    }), validators=[FileExtensionValidator(['mobi'])])
    file_pdf = forms.FileField(required=False, label=_('File pdf'), widget=forms.FileInput(attrs={
        'accept': '.pdf'
    }), validators=[FileExtensionValidator(['pdf'])])

    # uploader is added automatically in Views

    class Meta:
        model = Book
        fields = (
            'title',
            'author',
            'abstract',
            'cover',
            'file_epub',
            'file_mobi',
            'file_pdf',
        )
