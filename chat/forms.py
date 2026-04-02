# Third party imports
from django import forms

# Local folder imports
from .models import Room


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        # fields = ('title', 'allowed',)
        fields = ('title',)
