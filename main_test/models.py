from django.contrib.auth import get_user_model

from sdc_core.sdc_extentions.models import SdcModel
from sdc_core.sdc_extentions.forms import AbstractSearchForm
from django.template.loader import render_to_string
from sdc_core.sdc_extentions.search import handle_search_form
from django.db import models

User = get_user_model()
# Create your models here.

class AuthorSearchForm(AbstractSearchForm):
    CHOICES = (("name", "Name"), ('age', 'Age'))
    PLACEHOLDER = "Name, Title"
    DEFAULT_CHOICES = CHOICES[0][0]
    SEARCH_FIELDS = ("name", "book__title")

class Author(models.Model, SdcModel):
    edit_form = "main_test.forms.AuthorForm"
    create_form = "main_test.forms.AuthorForm"
    html_list_template = "main_test/models/Author/Author_list.html"
    html_detail_template = "main_test/models/Author/Author_details.html"

    name = models.CharField(max_length=255)
    age = models.IntegerField()

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):

        if template_name == cls.html_list_template:
            sf = AuthorSearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf,  range=2)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user, action, obj):
        return True

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()

class BookSearchForm(AbstractSearchForm):
    CHOICES = (("title", "Title"), ('author__name', 'Author'))
    PLACEHOLDER = "Book"
    DEFAULT_CHOICES = CHOICES[0][0]
    SEARCH_FIELDS = ('title', 'author__name')

class Book(models.Model, SdcModel):
    edit_form = "main_test.forms.BookForm"
    create_form = "main_test.forms.BookForm"
    html_list_template = "main_test/models/Book/Book_list.html"
    html_detail_template = "main_test/models/Book/Book_details.html"

    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.html_list_template:
            sf = BookSearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf,  range=20)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user, action, obj):
        return True

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()

class BookContentSearchForm(AbstractSearchForm):
    CHOICES = (("id", "Id"),)
    PLACEHOLDER = ""
    DEFAULT_CHOICES = CHOICES[0][0]
    SEARCH_FIELDS = ("id",)

class BookContent(models.Model, SdcModel):
    edit_form = "main_test.forms.BookContentForm"
    create_form = "main_test.forms.BookContentForm"
    html_list_template = "main_test/models/BookContent/BookContent_list.html"
    html_detail_template = "main_test/models/BookContent/BookContent_details.html"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.FileField()

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.html_list_template:
            sf = BookContentSearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf,  range=10)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user, action, obj):
        return user.is_authenticated

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.filter(user=user)
