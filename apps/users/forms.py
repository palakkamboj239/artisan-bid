from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.users.models import Profile, User


class UserRegistrationForm(UserCreationForm):
    """Elegant registration form for the luxury platform."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com"}),
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Choose a username"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Create a password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm your password"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class UserLoginForm(AuthenticationForm):
    """Clean login form with placeholders."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username or email"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )


class ProfileForm(forms.ModelForm):
    """Form for editing user profile."""

    class Meta:
        model = Profile
        fields = ("profile_picture", "bio", "account_type")
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Tell the world about yourself...",
                    "class": "form-control",
                }
            ),
        }
