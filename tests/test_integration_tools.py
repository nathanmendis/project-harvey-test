from django.test import TestCase
import json
from core.tools.email_tool import send_email_tool
from core.tools.calendar_tool import create_calendar_event_tool

class IntegrationToolsTest(TestCase):
    def test_send_email_tool(self):
        """Test the send_email_tool returns success placeholder."""
        recipient = "test@example.com"
        subject = "Hello"
        body = "World"
        
        # The tool returns a JSON string
        result_json = send_email_tool.invoke({
            "recipient_email": recipient,
            "subject": subject,
            "body": body
        })
        
        result = json.loads(result_json)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Email sent to {recipient}", result["message"])
        self.assertEqual(result["details"]["recipient"], recipient)
        self.assertEqual(result["details"]["subject"], subject)

    def test_create_calendar_event_tool(self):
        """Test the create_calendar_event_tool returns success placeholder."""
        title = "Team Meeting"
        start = "2023-10-27T10:00:00"
        end = "2023-10-27T11:00:00"
        attendees = "alice@example.com,bob@example.com"
        
        result_json = create_calendar_event_tool.invoke({
            "title": title,
            "start_time": start,
            "end_time": end,
            "attendees": attendees
        })
        
        result = json.loads(result_json)
        
        self.assertEqual(result["status"], "success")
        self.assertIn(f"Event '{title}' created", result["message"])
        self.assertEqual(result["details"]["title"], title)
        self.assertEqual(result["details"]["start"], start)
        self.assertEqual(result["details"]["attendees"], attendees)
