from sdc_core.sdc_extentions.models import SdcModel
from sdc_core.sdc_extentions.forms import AbstractSearchForm
from django.template.loader import render_to_string
from sdc_core.sdc_extentions.search import handle_search_form
from django.db import models

# Create your models here.



class TestOneModel(models.Model, SdcModel):
    class SearchForm(AbstractSearchForm):
        """A default search form used in the list view. You can delete it if you dont need it"""
        CHOICES = (("id", "Id"),)
        PLACEHOLDER = ""
        DEFAULT_CHOICES = CHOICES[0][0]
        SEARCH_FIELDS = ("id",)

    class _SdcMeta:
        """Meta data information needed to manage all SDC operations."""
        edit_form = "test_app_one.forms.TestOneModelForm"
        create_form = "test_app_one.forms.TestOneModelForm"
        html_list_template = "test_app_one/models/TestOneModel/TestOneModel_list.html"
        html_detail_template = "test_app_one/models/TestOneModel/TestOneModel_details.html"

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



class TestTwoModel(models.Model, SdcModel):
    class SearchForm(AbstractSearchForm):
        """A default search form used in the list view. You can delete it if you dont need it"""
        CHOICES = (("id", "Id"),)
        PLACEHOLDER = ""
        DEFAULT_CHOICES = CHOICES[0][0]
        SEARCH_FIELDS = ("id",)

    class _SdcMeta:
        """Meta data information needed to manage all SDC operations."""
        edit_form = "test_app_one.forms.TestTwoModelForm"
        create_form = "test_app_one.forms.TestTwoModelForm"
        html_list_template = "test_app_one/models/TestTwoModel/TestTwoModel_list.html"
        html_detail_template = "test_app_one/models/TestTwoModel/TestTwoModel_details.html"

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
