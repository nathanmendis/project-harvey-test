"""
ASGI config for project_harvey project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_harvey.settings')

# application = get_asgi_application()


# your_project_name/asgi.py

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from core import routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

application = ProtocolTypeRouter({
    "http": ASGIStaticFilesHandler(get_asgi_application()),  # ✅ serves static files in dev
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
