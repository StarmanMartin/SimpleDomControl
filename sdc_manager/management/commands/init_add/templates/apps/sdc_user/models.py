import datetime

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
# add django-phone-field>=	1.8.1 to your requirements.txt
# from phone_field import PhoneField
from django.db import models


from django.utils.crypto import get_random_string
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, username, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('A user needs an unique e-mail'))

        if not username:
            raise ValueError(_('Username/Abbreviation must be 3 characters long'))

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, username, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, username, password, **extra_fields)


def getUUID():
    return get_random_string(length=32)

NATIONS = (('D', _('Germany')), ('G', _('Greek')))

class CustomUser(AbstractUser):
    email = models.EmailField(_('E-mail'), unique=True, null=True)
    username = models.CharField(_('Abbreviation'), max_length=255, unique=True, blank=False,null=False)
    #phone = PhoneField(_('Contact phone number'), help_text=_('Phone number, only for emergency'), null=True, blank=False)

    # birth_date = models.DateField(_('Birthday'), null=True, blank=False)

    is_email_confirmed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'username'

    objects = CustomUserManager()

    agb = models.BooleanField(blank=False, default=False,null=False)


    def send_confirm_email(self, request):
        link = EmailLink.objects.create(email_confirm_link=getUUID(),
                                        is_confirmed_date=datetime.date.today(),
                                        user=self,
                                        email_type='C')

        email_template_name = 'sdc_user/email/confirm_email.html'

        context = {'user': self, 'link': link}

        html_content = render_to_string(email_template_name, request=request, context=context)

        msg = EmailMessage(_('Confirm Email'), html_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[self.email])
        msg.content_subtype = "html"  # Main content is now text/html
        msg.send(fail_silently=True)


    def __str__(self):
        return self.email


class EmailLink(models.Model):
    email_confirm_link = models.CharField(max_length=255, null=True)
    is_confirmed_date = models.DateField(null=True)
    user = models.ForeignKey('sdc_user.CustomUser', on_delete=models.CASCADE)
    email_type = models.CharField(max_length=1)
    is_done = models.BooleanField(default=False)


