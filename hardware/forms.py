from django import forms
from hardware.models import Card


class CreateCard(forms.ModelForm):
    class Meta:
        model = Card
        fields = [
            "key",
            "operator",
            "user",
        ]  # 'enabled' relies on the model default (True) and is not user-editable in this form
        widgets = {"user": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
