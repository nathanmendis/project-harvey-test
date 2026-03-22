import datetime
from django.utils import timezone
from core.models.leaves import LeaveRequest
from core.models.chatbot import Message

def get_proactive_greeting(user):
    """Generates a complete, token-free contextual greeting based on time, actionable tasks, and sticky memory."""
    now = timezone.now()
    hour = now.hour
    weekday = now.weekday()
    
    # 1. Base Greeting
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    greeting = f"{greeting} {user.name or user.username} 👋!"

    # 2. Priority: Pending Actionable Tasks
    if user.role in ['manager', 'org_admin']:
        pending_count = LeaveRequest.objects.filter(status='pending', organization=user.organization).count()
        if pending_count > 0:
            return f"{greeting} You have {pending_count} pending leave requests to approve over in the dashboard."
    
    # Check for unapproved leaves for this specific employee
    unapproved_leaves = LeaveRequest.objects.filter(status='pending', employee=user).count()
    if unapproved_leaves > 0:
        return f"{greeting} Note: Your latest leave request is still waiting for manager approval."

    # 3. Lifecycle Nudges
    if user.date_joined:
        days_employed = (now.date() - user.date_joined.date()).days
        if days_employed == 7:
            return f"{greeting} Happy 1-week anniversary! 🎉 Let me know if you need help finding any policies."
        elif days_employed == 365:
            return f"{greeting} Happy 1-Year Work Anniversary! 🎂 Hope you have a great day."

    # 4. Try Sticky Memory
    yesterday = now - datetime.timedelta(days=1)
    # Search for the user's most recent interaction
    last_user_msg = Message.objects.filter(
        conversation__user=user, 
        sender='user', 
        timestamp__gte=yesterday
    ).order_by('-timestamp').first()
    
    if last_user_msg:
        decrypted_text = last_user_msg.text
        if decrypted_text and len(decrypted_text) < 60:
            return f"{greeting} Yesterday you were asking about '{decrypted_text}'. Did you get what you needed?"

    # 5. Fallback Time Context
    if weekday == 0 and hour < 12:
        return f"{greeting} Ready to tackle the week?"
    elif weekday == 4 and hour > 14:
        return f"{greeting} Happy Friday! Wrapping things up before the weekend?"
        
    return f"{greeting} How can I help you today?"
