from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from core.api import PolicyViewSet
from django.http import HttpResponse

def favicon_view(request):
    return HttpResponse(status=204)

router = DefaultRouter()
router.register(r'policies', PolicyViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('core.urls')),
    path('adminpanel/', include('adminpanel.urls')),
    path('integrations/', include('integrations.urls')),
    path('api/', include(router.urls)),
    path("__reload__/", include("django_browser_reload.urls")),
    path("favicon.ico", favicon_view),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
