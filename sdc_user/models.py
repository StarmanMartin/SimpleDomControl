from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from sdc_core.sdc_extentions.models import SdcModel
from sdc_core.sdc_extentions.forms import AbstractSearchForm
from django.template.loader import render_to_string
from sdc_core.sdc_extentions.search import handle_search_form
from django.utils.translation import gettext_lazy as _

from sdc_user.mails import send_confirm_email
from django.utils.module_loading import import_string

def sdc_user_is_authorised(user, action, obj):
    return user.is_authenticated

_sdc_user_is_authorised = import_string(settings.SDC_USER_IS_AUTHORISED)

def sdc_user_get_queryset(sdc_user_cls, user, action, obj):
    if user.is_superuser:
        return sdc_user_cls.objects.all()
    else:
        return sdc_user_cls.objects.filter(pk=user.pk)

_sdc_user_get_queryset = import_string(settings.SDC_USER_GET_QUERYSET)

class SdcUser(AbstractUser, SdcModel):
    email_confirmed = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._origen_email = self.email


    class SearchForm(AbstractSearchForm):
        """A default search form used in the list view. You can delete it if you dont need it"""
        CHOICES = (("username", _("Username")),("first_name", _("first_name")),("Last name", _("Last name")),)
        PLACEHOLDER = ""
        DEFAULT_CHOICES = CHOICES[0][0]
        SEARCH_FIELDS = ("username", 'first_name', 'last_name', 'email')

    class Meta:
        swappable = "AUTH_USER_MODEL"

    class SdcMeta:
        """Meta data information needed to manage all SDC operations."""
        edit_form = "sdc_user.forms.SdcUserChangeForm"
        create_form = "sdc_user.forms.SdcUserCreationForm"
        password_form = "sdc_user.forms.SdcUserPassword"
        html_list_template = "sdc_user/models/SdcUser/SdcUser_list.html"
        html_detail_template = "sdc_user/models/SdcUser/SdcUser_details.html"
        fields = settings.SDC_USER_FIELDS
        exclude = settings.SDC_USER_FIELDS_EXCLUDE

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.SdcMeta.html_list_template:
            sf = cls.SearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf,  range=10)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user, action, obj):
        return _sdc_user_is_authorised(user, action, obj)

    @classmethod
    def get_queryset(cls, user, action, obj):
        return _sdc_user_get_queryset(cls, user, action, obj)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.email != self._origen_email:
            send_confirm_email(self)
