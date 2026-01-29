# core/urls.py
from django.urls import path
from .views import chat_with_llm, chat_page, login_view, CustomLogoutView, upload_resume, landing_page


urlpatterns = [
    path('login/', login_view, name='login'),
    path('', landing_page, name='landing_page'),
    path("app/", chat_page, name="chat_view"),
    path("chat/", chat_with_llm, name="chat_with_llm"),
    path("upload_resume/", upload_resume, name="upload_resume"),
    path('logout/', CustomLogoutView.as_view(next_page='login'), name='logout'),


    
]
