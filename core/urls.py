# core/urls.py
from django.urls import path
from .views import chat_with_llm ,chat_page

urlpatterns = [
    path("", chat_page, name="chat_view"),
    path("chat/", chat_with_llm, name="chat_with_llm"),
    
]
