from django.urls import path, re_path
from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('sdc_logout', sdc_views.SdcLogout.as_view(), name='scd_view_sdc_logout'),
    path('sdc_login', sdc_views.SdcLogin.as_view(), name='scd_view_sdc_login'),
]
