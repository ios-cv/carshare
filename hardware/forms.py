from django import forms
from users.models import User
from hardware.models import Card


class CreateCard(forms.ModelForm):
    class Meta:
        model = Card
        fields = ["key", "operator", "user"]
        widgets = {"user": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
