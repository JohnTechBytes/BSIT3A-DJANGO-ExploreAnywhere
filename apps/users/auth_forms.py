"""Account forms used by the public sign-up flow and by the staff admin.

``django.contrib.auth.forms.UserCreationForm`` / ``UserChangeForm`` hard-code
``auth.User`` as their model, which raises *"Cannot use model auth.User because
it has been swapped out"* once ``AUTH_USER_MODEL`` points at ``users.User``.
The two admin forms below simply re-bind them to the real user model.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils import timezone

User = get_user_model()


class ExploreRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    consent_privacy = forms.BooleanField(
        label="I have read and agree to the Privacy Notice",
        error_messages={
            "required": "Please read and accept the Privacy Notice to create an account.",
        },
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.USER
        user.is_staff = False
        user.is_superuser = False
        # The acceptance of the privacy notice is stored with the account.
        user.consent_privacy = True
        user.consent_privacy_at = timezone.now()
        if commit:
            user.save()
        return user


class ExploreUserCreationForm(UserCreationForm):
    """Admin "add account" form bound to the swapped-in ``users.User`` model."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")


class ExploreUserChangeForm(UserChangeForm):
    """Admin "change account" form bound to the swapped-in ``users.User`` model."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
