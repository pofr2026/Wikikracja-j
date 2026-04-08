# Third party imports
from django import forms
from django.core.exceptions import ValidationError

# Local folder imports
from .models import Room


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        # fields = ('title', 'allowed',)
        fields = ('title',)

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            # Check for case-insensitive duplicate
            if Room.objects.filter(title__iexact=title).exists():
                raise ValidationError(
                    "Pokój o tej nazwie juz istnieje (niezaleznie od wielkosci liter).",
                    code='duplicate_title'
                )
        return title
