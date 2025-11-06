# core/urls.py
from django.urls import path
from .views import chat_with_llm ,chat_page,login_view ,CustomLogoutView


urlpatterns = [
    path('login/', login_view, name='login'),
    path("", chat_page, name="chat_view"),
    path("chat/", chat_with_llm, name="chat_with_llm"),
    path('logout/', CustomLogoutView.as_view(next_page='login'), name='logout'),


    
]
