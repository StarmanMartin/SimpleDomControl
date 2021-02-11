from django.conf.urls import url
from django.urls import path
from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('login_view', sdc_views.LoginView.as_view(), name='scd_view_login_view'),
]
