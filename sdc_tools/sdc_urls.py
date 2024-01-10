from django.urls import path

from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('sdc_dummy', sdc_views.SdcDummy.as_view(), name='scd_view_sdc_dummy'),
    path('sdc_error/<int:code>', sdc_views.SdcError.as_view(), name='scd_view_sdc_error'),
    path('sdc_alert_messenger', sdc_views.SdcAlertMessenger.as_view(), name='scd_view_sdc_alert_messenger'),
    path('sdc_search_view', sdc_views.SdcSearchView.as_view(), name='scd_view_sdc_search_view'),
    path('sdc_detail_view', sdc_views.SdcDetailView.as_view(), name='scd_view_sdc_detail_view'),
    path('sdc_model_form', sdc_views.SdcModelForm.as_view(), name='scd_view_sdc_model_form'),
    path('sdc_list_view', sdc_views.SdcListView.as_view(), name='scd_view_sdc_list_view'),
    path('sdc_navigator', sdc_views.SdcNavigator.as_view(), name='scd_view_sdc_navigator'),
]
