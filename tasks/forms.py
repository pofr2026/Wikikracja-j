# Third party imports
from django import forms
from django.utils.translation import gettext_lazy as _

# Local folder imports
from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6
            }),
        }


class TaskStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (Task.Status.COMPLETED, Task.Status.COMPLETED.label),
            (Task.Status.CANCELLED, Task.Status.CANCELLED.label),
        ]

    class Meta:
        model = Task
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={
                "class": "form-control"
            }),
        }

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status not in (Task.Status.COMPLETED, Task.Status.CANCELLED):
            raise forms.ValidationError(_("Invalid closing status."))
        return status
