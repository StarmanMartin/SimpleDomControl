from django.urls import path, re_path
from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('test_item', sdc_views.TestItem.as_view(), name='scd_view_test_item'),
    path('error_404', sdc_views.Error404.as_view(), name='scd_view_error_404'),
    path('logged_in', sdc_views.LoggedIn.as_view(), name='scd_view_logged_in'),
    path('editor_no_staff', sdc_views.EditorNoStaff.as_view(), name='scd_view_editor_no_staff'),
    path('editor_and_staff', sdc_views.EditorAndStaff.as_view(), name='scd_view_editor_and_staff'),
    path('staff_and_admin', sdc_views.StaffAndAdmin.as_view(), name='scd_view_staff_and_admin'),
    path('admin_only', sdc_views.AdminOnly.as_view(), name='scd_view_admin_only'),
    path('main_view', sdc_views.MainView.as_view(), name='scd_view_main_view'),
]
