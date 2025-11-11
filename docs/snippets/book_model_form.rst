.. code-block:: python

    from main_app.models import Review
    from main_app.models import Book
    from django.forms.models import ModelForm


    # Form Model Book

    class BookForm(ModelForm):
        class Meta:
            model = Book
            fields = "__all__"

*./Library/main_app/forms.py*