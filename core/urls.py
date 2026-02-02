# core/urls.py
from django.urls import path
from .views import (
    chat_with_llm, chat_page, login_view, CustomLogoutView, upload_resume, landing_page,
    google_login, google_callback, org_google_login
)
from .api import list_conversations, get_conversation_messages
from adminpanel import views as admin_views

urlpatterns = [
    path('login/', login_view, name='login'),
    # ... other paths ...
    path('adminpanel/invites/', admin_views.manage_invites, name='manage_invites'),
    path('adminpanel/invites/revoke/<int:invite_id>/', admin_views.delete_invite, name='delete_invite'),
    path('auth/google/login/', google_login, name='google_login'),
    # Org specific login
    path('auth/google/org/login/', org_google_login, name='org_google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),
    path('', landing_page, name='landing_page'),
    path("app/", chat_page, name="chat_view"),
    path("chat/", chat_with_llm, name="chat_with_llm"),
    path("api/conversations/", list_conversations, name="list_conversations"),
    path("api/conversations/<int:conversation_id>/messages/", get_conversation_messages, name="get_conversation_messages"),
    path("upload_resume/", upload_resume, name="upload_resume"),
    path('logout/', CustomLogoutView.as_view(next_page='login'), name='logout'),
]
