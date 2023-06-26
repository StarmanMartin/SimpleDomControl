from test_app_one.models import TestTwoModel
from test_app_one.models import TestOneModel
from django.forms.models import ModelForm


# Form Model TestOneModel

class TestOneModelForm(ModelForm):
    class Meta:
        model = TestOneModel
        fields = "__all__"



# Form Model TestTwoModel

class TestTwoModelForm(ModelForm):
    class Meta:
        model = TestTwoModel
        fields = "__all__"
