from django.urls import path

from . import sdc_views

# Do not add an app_name to this file

urlpatterns = [
    # scd view below
    path('global_dom_events', sdc_views.GlobalDomEvents.as_view(), name='scd_view_global_dom_events'),
    path('auto_submit_mixin', sdc_views.AutoSubmitMixin.as_view(), name='scd_view_auto_submit_mixin'),
    path('search_controller', sdc_views.SearchController.as_view(), name='scd_view_search_controller'),
    path('change_sync_mixin', sdc_views.ChangeSyncMixin.as_view(), name='scd_view_change_sync_mixin'),
    path('g_alert_msg', sdc_views.GAlertMsg.as_view(), name='scd_view_g_alert_msg'),
    path('list_mixin', sdc_views.ListMixin.as_view(), name='scd_view_list_mixin'),
    path('nav_client', sdc_views.NavClient.as_view(), name='scd_view_nav_client'),
    path('nav_view', sdc_views.NavView.as_view(), name='scd_view_nav_view'),
]
