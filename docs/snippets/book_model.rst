.. code-block:: python

    ...
    class Book(models.Model, SdcModel):
        title = models.CharField(max_length=100)
        author = models.CharField(max_length=100)
        text = models.CharField(max_length=255, default=default_text)
        borrowed_by = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

        class SearchForm(AbstractSearchForm):
            """A default search form used in the list view. You can delete it if you dont need it"""
            CHOICES = (("title", "Title"), ("author", "Author"),)
            PLACEHOLDER = "Title or Author"
            DEFAULT_CHOICES = CHOICES[0][0]
            SEARCH_FIELDS = ("title", "author")

        class _SdcMeta:
            """Meta data information needed to manage all SDC operations."""
            edit_form = "main_app.forms.BookForm"
            create_form = "main_app.forms.BookForm"
            html_list_template = "main_app/models/Book/Book_list.html"
            html_detail_template = "main_app/models/Book/Book_details.html"

        @classmethod
        def render(cls, template_name, context=None, request=None, using=None):
            if template_name == cls.SdcMeta.html_list_template:
                sf = cls.SearchForm(data=context.get("filter", {}))
                context = context | handle_search_form(context["instances"], sf, range=3)
            return render_to_string(template_name=template_name, context=context, request=request, using=using)

        @classmethod
        def is_authorised(cls, user, action, obj):
                return True

        @classmethod
        def get_queryset(cls, user, action, obj):
            return cls.objects.all()

*./Library/main_app/models.py*