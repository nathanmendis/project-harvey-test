from django.test import TestCase, Client
from django.urls import reverse
from core.models.organization import Organization, User
from core.models.recruitment import LeaveRequest
from django.utils import timezone
import datetime

class LeaveApprovalTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(name="Tech Corp")
        self.admin = User.objects.create_user(username="admin", password="password", organization=self.org)
        self.admin.is_org_admin = True
        self.admin.save()
        self.client.login(username="admin", password="password")
        
        self.leave = LeaveRequest.objects.create(
            organization=self.org,
            employee=self.admin,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=2),
            leave_type="Sick",
            status="pending"
        )

    def test_approve_leave(self):
        url = reverse('approve_leave', args=[self.leave.id])
        
        # Verify initial status
        self.assertEqual(self.leave.status, 'pending')
        
        # Post to approve
        response = self.client.post(url, follow=True)
        
        print(f"URL: {url}")
        print(f"Redirect chain: {response.redirect_chain}")
        print(f"Final Status: {response.status_code}")

        # Check redirect
        # self.assertRedirects(response, reverse('leave_detail', args=[self.leave.id]))
        
        # Check status updated
        self.leave.refresh_from_db()
        self.assertEqual(self.leave.status, 'approved')
        
        # Check message (optional, but good)
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), f"Leave request for {self.admin.username} has been approved.")
