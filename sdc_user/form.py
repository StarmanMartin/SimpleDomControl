import datetime
from datetime import date

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from sdc_tools.django_extension.forms import CaptchaField
from .models import CustomUser, EmailLink, getUUID
from django.core.mail import EmailMessage

class CustomUserCreationForm(UserCreationForm):
    phone = forms.RegexField(regex=r'^\+?1?\d{4,15}$',
                             error_messages={'invalid': _('We need a phone number in case of emergency.')})

    chapter = CaptchaField()

    birth_date = forms.DateField(label=_('Birthday'), widget=forms.DateInput(attrs={
        'class': 'datepicker',
        'type': "text",
        'data-date-max': date.today().strftime("%d.%m.%Y"),
        'data-date-min': '01.01.1930'
    }, format='%d.%m.%Y'),
                                 input_formats=('%d.%m.%Y',),
                                 required=False)

    agb = forms.BooleanField(label=_('Terms and conditions'), help_text=_(
        'Read the terms and conditions <a href="%ssdc_user/forms/agb.pdf" target="_blank">here</a>') % settings.STATIC_URL,
                             required=False)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'birth_date', 'phone', 'street', 'zip', 'city', 'land', 'agb')

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        super(CustomUserCreationForm, self).save(commit)


class CustomEditForm(UserChangeForm):
    phone = forms.RegexField(regex=r'^\+?1?\d{4,15}$',
                             error_messages={'invalid': _('We need a phone number in case of emergency.')})

    email_help_text = _(
        'Raw passwords are not stored, so there is no way to see this '
        'user’s password, but you can change the password using '
        '<a href="{}">this form</a>.'
    ),

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone', 'street', 'zip', 'city', 'land', 'password')

    def __init__(self, instance, *args, **kwargs):
        self.origin_email = instance.email
        super(CustomEditForm, self).__init__(instance=instance, *args, **kwargs)
        password = self.fields.get('password')
        if password:
            password.help_text = self.email_help_text[0].format('user-change-password" class="password-change')

    def prepare_save(self, request):
        ret_val = False

        if self.cleaned_data['email'] != self.origin_email:
            self.instance.is_email_confirmed = False
            self.send_confirm_email(request)
            ret_val = True

        return ret_val


class PasswordResetForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )

    def send_mail(self, request, user):
        link = EmailLink.objects.create(email_confirm_link=getUUID(),
                                        is_confirmed_date=datetime.date.today(),
                                        user=user,
                                        email_type='P')

        email_template_name = 'sdc_user/email/confirm_pw_reset_email.html'

        context = {'user': self, 'link': link}

        html_content = render_to_string(email_template_name, request=request, context=context)

        msg = EmailMessage(_('Change password'), html_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
        msg.content_subtype = "html"  # Main content is now text/html
        msg.send(fail_silently=True)

    def get_users(self, email):
        return CustomUser.objects.get(email=email)

    def save(self, request):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        email = self.cleaned_data["email"]
        try:
            user = self.get_users(email)
            user.save()
            self.send_mail(request, user)
        except Exception as e:
            print(e)
            pass
