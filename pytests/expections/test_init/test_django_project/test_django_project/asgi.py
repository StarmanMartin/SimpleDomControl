"""
ASGI config for test_django_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

To run it using daphne set DEBUG to false and then execute the following commmand:
env ALLOWED_HOST=http://localhost:8000 daphne test_django_project.asgi:application

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ElnAdapter.settings')

import django
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from . import routing
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})