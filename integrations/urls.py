from django.urls import path
from . import views

urlpatterns = [
    path('oauth/start/<str:provider>/', views.start_oauth, name='start_oauth'),
    path('oauth/callback/<str:provider>/', views.oauth_callback, name='oauth_callback'),
]
