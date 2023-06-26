from django.urls import path, re_path
from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('test_sdc_one', sdc_views.TestSdcOne.as_view(), name='scd_view_test_sdc_one'),
]
