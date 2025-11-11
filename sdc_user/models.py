from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from sdc_core.sdc_extentions.models import SdcModel
from sdc_core.sdc_extentions.forms import AbstractSearchForm
from django.template.loader import render_to_string
from sdc_core.sdc_extentions.search import handle_search_form
from django.utils.translation import gettext_lazy as _

from sdc_user.mails import send_confirm_email


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
        abstract = settings.AUTH_USER_MODEL != "sdc_user.SdcUser"

    class _SdcMeta:
        """Meta data information needed to manage all SDC operations."""
        edit_form = "sdc_user.forms.SdcUserChangeForm"
        create_form = "sdc_user.forms.SdcUserCreationForm"
        password_form = "sdc_user.forms.SdcUserPassword"
        html_list_template = "sdc_user/models/SdcUser/SdcUser_list.html"
        html_detail_template = "sdc_user/models/SdcUser/SdcUser_details.html"

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.SdcMeta.html_list_template:
            sf = cls.SearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf,  range=10)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user, action, obj):
        return True

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.email != self._origen_email:
            send_confirm_email(self)
