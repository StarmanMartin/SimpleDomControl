from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password, password_validators_help_text_html

from sdc_user.models import SdcUser
from sdc_user.widgets import ReadOnlyPassword


class SdcUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput,
                                help_text=password_validators_help_text_html())
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = SdcUser
        fields = ("username", "first_name", "last_name", "email")

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1, user=None)
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don’t match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class SdcUserPassword(forms.ModelForm):
    password_old = forms.CharField(label="Current password", widget=forms.PasswordInput)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput,
                                help_text=password_validators_help_text_html())
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = SdcUser
        fields = ()

    def clean_password_old(self):
        password_old = self.cleaned_data.get("password_old")
        if not self.instance.check_password(password_old):
            raise forms.ValidationError("Password doesn't match")

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1, user=self.instance)
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don’t match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class SdcUserChangeForm(forms.ModelForm):
    password = forms.Field(widget=ReadOnlyPassword())

    class Meta:
        model = SdcUser
        fields = ("username", "first_name", "last_name", "email", 'password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.user = self.instance


class PasswordResetConfirmForm(forms.Form):
    password = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={'placeholder': _('New password')}),
        strip=False,
        min_length=8,
        help_text=password_validators_help_text_html()
    )
    password_repeat = forms.CharField(
        label="Repeat password",
        widget=forms.PasswordInput(attrs={'placeholder': _('Repeat password')}),
        strip=False,
        min_length=8,
    )
    token = forms.CharField(widget=forms.HiddenInput())

    def clean_password(self):
        password1 = self.cleaned_data.get("password")
        validate_password(password1, user=None)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_repeat = cleaned_data.get("password_repeat")

        if password != password_repeat:
            self.add_error("password_repeat", _("Passwords do not match."))
        return cleaned_data
