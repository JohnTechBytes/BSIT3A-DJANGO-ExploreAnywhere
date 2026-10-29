"""The System Usability Scale form.

The ten item wordings live on the ``SusResponse`` model fields, so the survey
and the stored record can never drift apart.
"""
from django import forms

from apps.info.models import SusResponse

SCALE_CHOICES = [(value, str(value)) for value in range(1, 6)]


class SusForm(forms.Form):
    """The ten standard SUS items, each answered on a 1-5 agreement scale."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for index in range(1, 11):
            name = f"q{index}"
            self.fields[name] = forms.ChoiceField(
                choices=SCALE_CHOICES,
                label=SusResponse._meta.get_field(name).help_text,
                widget=forms.RadioSelect,
                required=True,
            )

    def response(self, user=None):
        """Build the (unsaved) SusResponse for the cleaned answers."""
        response = SusResponse(user=user)
        for index in range(1, 11):
            setattr(response, f"q{index}", int(self.cleaned_data[f"q{index}"]))
        response.compute_score()
        return response
