from abc import ABC, abstractmethod

class OAuthService(ABC):
    def __init__(self, user):
        self.user = user

    @abstractmethod
    def get_auth_url(self):
        """Returns the URL to redirect the user to for authentication."""
        pass

    @abstractmethod
    def handle_callback(self, code):
        """Exchanges the code for tokens and saves them."""
        pass

    @abstractmethod
    def get_credentials(self):
        """Retrieves stored credentials for the user."""
        pass

class EmailService(OAuthService):
    @abstractmethod
    def send_email(self, recipient_email, subject, body):
        """Sends an email."""
        pass

class CalendarService(OAuthService):
    @abstractmethod
    def create_event(self, title, start_time, end_time, attendees=None, description=None):
        """Creates a calendar event."""
        pass
