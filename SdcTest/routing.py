from django.urls import re_path

from sdc_core import consumers

websocket_urlpatterns = [
    re_path(r'sdc_ws/ws/$', consumers.SDCConsumer.as_asgi()),
    re_path(r'sdc_ws/model/(?P<model_name>\w+)$', consumers.SDCModelConsumer.as_asgi()),
    re_path(r'sdc_ws/model/(?P<model_name>\w+)/(?P<model_id>\d+)', consumers.SDCModelConsumer.as_asgi()),
]