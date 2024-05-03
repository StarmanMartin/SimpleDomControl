from main_test.models import BookContent
from main_test.models import Book
from main_test.models import Author
from django.forms.models import ModelForm


# Form Model Author

class AuthorForm(ModelForm):
    class Meta:
        model = Author
        fields = "__all__"



# Form Model Book

class BookForm(ModelForm):
    class Meta:
        model = Book
        fields = "__all__"



# Form Model Book

class SmallBookForm(ModelForm):
    class Meta:
        model = Book
        fields = ("title",)



# Form Model BookCover

class BookContentForm(ModelForm):
    class Meta:
        model = BookContent
        fields = "__all__"
