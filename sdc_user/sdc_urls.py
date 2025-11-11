from django.urls import path
from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('sdc_reset_password', sdc_views.SdcResetPassword.as_view(), name='scd_view_sdc_reset_password'),
    path('sdc_password_forgotten', sdc_views.SdcPasswordForgotten.as_view(), name='scd_view_sdc_password_forgotten'),
    path('sdc_change_password', sdc_views.SdcChangePassword.as_view(), name='scd_view_sdc_change_password'),
    path('sdc_user', sdc_views.SdcUser.as_view(), name='scd_view_sdc_user'),
    path('sdc_confirm_email/<str:token>', sdc_views.SdcConfirmEmail.as_view(), name='scd_view_sdc_confirm_email'),
    path('sdc_user_nav_btn', sdc_views.SdcUserNavBtn.as_view(), name='scd_view_sdc_user_nav_btn'),
    path('sdc_logout', sdc_views.SdcLogout.as_view(), name='scd_view_sdc_logout'),
    path('sdc_login', sdc_views.SdcLogin.as_view(), name='scd_view_sdc_login'),
]
