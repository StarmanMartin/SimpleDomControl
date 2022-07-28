from django.urls import path, re_path
from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('user_edit', sdc_views.UserEdit.as_view(), name='scd_view_user_edit'),
    path('user_change_password', sdc_views.UserChangePassword.as_view(), name='scd_view_user_change_password'),
    path('user_password_reset', sdc_views.UserPasswordReset.as_view(), name='scd_view_user_password_reset'),
    path('user_info', sdc_views.UserInfo.as_view(), name='scd_view_user_info'),
    path('user_password_forgotten', sdc_views.UserPasswordForgotten.as_view(), name='scd_view_user_password_forgotten'),
    path('user_logout', sdc_views.UserLogout.as_view(), name='scd_view_user_logout'),
    re_path('user_confirm_email/(?P<key>[a-zA-Z0-9]{32})', sdc_views.UserConfirmEmail.as_view(), name='scd_view_user_confirm_email'),
    path('user_register', sdc_views.UserRegister.as_view(), name='scd_view_user_register'),
    path('user_manager', sdc_views.UserManager.as_view(), name='scd_view_user_manager'),
    path('login_view', sdc_views.LoginView.as_view(), name='scd_view_login_view'),
]
