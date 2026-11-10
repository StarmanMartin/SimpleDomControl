"""
Routes of the REST API; include them with ``path('sdc_api/', include('sdc_core.api_urls'))``.

The fixed routes come before ``<str:model>/``: SdcModels named ``Login``, ``Tokens`` or ``Account`` are not
reachable through the REST API.
"""
from django.urls import path

from sdc_core.rest_api import AccountView, AdcApi, ApiTokenView, ApiTokensView, current_token, get_api_token

urlpatterns = [
    path('login/', get_api_token, name='sdc_api_login'),
    path('tokens/', ApiTokensView.as_view(), name='sdc_api_tokens'),
    path('tokens/current/', current_token, name='sdc_api_token_current'),
    path('tokens/<uuid:token_id>/', ApiTokenView.as_view(), name='sdc_api_token'),
    path('account/', AccountView.as_view(), name='sdc_api_account'),
    path('<str:model>/<int:id>/', AdcApi.as_view(), name='sdc_api_object'),
    path('<str:model>/', AdcApi.as_view(), name='sdc_api_list'),
]
