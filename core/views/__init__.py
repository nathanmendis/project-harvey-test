from .pages import landing_page, docs_view, docs_print_view
from .auth import (
    login_view, 
    CustomLogoutView, 
    google_login, 
    google_callback, 
    org_google_login,
    password_reset_confirm,
    admin_google_system_login
)
from .chat import chat_page, chat_with_llm
from .upload import upload_resume
