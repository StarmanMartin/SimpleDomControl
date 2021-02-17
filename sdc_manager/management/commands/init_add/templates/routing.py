from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'sdc_ws/ws/$', consumers.SDCConsumer.as_asgi()),
]