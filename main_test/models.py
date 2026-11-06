from django.contrib.auth import get_user_model

from sdc_core.sdc_extentions.models import SdcModel
from sdc_core.sdc_extentions.forms import AbstractSearchForm
from django.template.loader import render_to_string
from sdc_core.sdc_extentions.search import handle_search_form
from django.db import models


# Create your models here.

class AuthorSearchForm(AbstractSearchForm):
    CHOICES = (("name", "Name"), ('age', 'Age'))
    PLACEHOLDER = "Name, Title"
    DEFAULT_CHOICES = CHOICES[0][0]
    SEARCH_FIELDS = ("name", "book__title")

class Author(models.Model, SdcModel):
    """
    Demo/test model of the framework's test project: an author of `Book` records.

    - `name` (text, max. 255 characters) and `age` (integer, years); both required.
    - Has no permission checks: anyone, even anonymous users, may read, create, edit and delete authors.
    - Deleting an author also deletes all of that author's `Book` records.
    - The list search matches `name` or the title of one of the author's books.
    - Calling the `call_echo` / `call_async_echo` server calls of `<main-view>` creates an extra author `XX FF` (age `2`).
    """
    edit_form = "main_test.forms.AuthorForm"
    create_form = "main_test.forms.AuthorForm"
    html_list_template = "main_test/models/Author/Author_list.html"
    html_detail_template = "main_test/models/Author/Author_details.html"

    name = models.CharField(max_length=255)
    age = models.IntegerField()

    def __str__(self):
        # Shown in the author list and its "Remove <author>" buttons
        return self.name

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
    """
    Demo/test model of the framework's test project: a book with a title, written by one `Author`.

    - `title` (text, max. 255 characters); `author` → `Author` (required).
    - Has no permission checks: anyone, even anonymous users, may read, create, edit and delete books.
    - Deleted automatically when its `Author` is deleted.
    - Besides the full form there is a named form `test` that edits only `title`.
    - The list search matches `title` or the author's `name`.
    - Edited in `<book-edit>`.
    """

    class _SdcMeta:
        edit_form = "main_test.forms.BookForm"
        create_form = "main_test.forms.BookForm"
        html_list_template = "main_test/models/Book/Book_list.html"
        html_detail_template = "main_test/models/Book/Book_details.html"
        test = "main_test.forms.SmallBookForm"

    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.SdcMeta.html_list_template:
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
    """
    Demo/test model of the framework's test project: an uploaded file that belongs to one user.

    - `text`: the uploaded file; `user` → the owning user.
    - If `user` is left empty on save, the currently logged-in user becomes the owner.
    - Only logged-in users may access it, and each user sees and changes only their own records.
    - Deleting the user also deletes the user's `BookContent` records.
    """

    edit_form = "main_test.forms.BookContentForm"
    create_form = "main_test.forms.BookContentForm"

    user = models.ForeignKey(get_user_model(), blank=True, on_delete=models.CASCADE)
    text = models.FileField()

    @classmethod
    def render(cls, template_name, context=None, request=None, using=None):
        if template_name == cls.SdcMeta.html_list_template:
            sf = BookContentSearchForm(data=context.get("filter", {}))
            context = context | handle_search_form(context["instances"], sf,  range=10)
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user, action, obj):
        return user.is_authenticated

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.filter(user=user)

    def save(self, *args, **kwargs):
        if self.user_id is None:
            self.user = self.scope['user']
        super().save(*args, **kwargs)
