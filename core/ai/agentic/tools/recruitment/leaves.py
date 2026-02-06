from langchain_core.tools import tool
from core.models.recruitment import LeaveRequest
from core.ai.agentic.tools.utils import ok, err, get_org

@tool("list_leave_requests", return_direct=True)
def list_leave_requests(status: str = "pending", user=None) -> str:
    """
    Lists leave requests. Default shows pending requests.
    status options: 'pending', 'approved', 'rejected', 'all'.
    """
    org = get_org(user)
    if not org:
        return err("User error.")

    leaves = LeaveRequest.objects.filter(organization=org)
    
    if status != 'all':
        leaves = leaves.filter(status__iexact=status)
        
    leaves = leaves.order_by('-start_date')

    if not leaves.exists():
        return ok(f"No {status} leave requests found.")

    lines = [f"Found {leaves.count()} {status} leave request(s):"]
    results = []
    
    for l in leaves:
        duration = (l.end_date - l.start_date).days + 1
        lines.append(f"• **{l.employee.name}**: {l.leave_type} for {duration} day(s) ({l.start_date} to {l.end_date})")
        results.append({"id": l.id, "employee": l.employee.name, "status": l.status})

    return ok("\n".join(lines), results=results)


@tool("apply_leave", return_direct=True)
def apply_leave(start_date: str, end_date: str, leave_type: str, reason: str, user=None) -> str:
    """
    Submits a leave request for the current user.
    start_date/end_date: ISO 8601 (YYYY-MM-DD) preferred, but natural language (e.g., 'next Monday') is accepted.
    leave_type: e.g., 'Sick', 'Casual', 'Annual'.
    """
    org = get_org(user)
    if not org:
        return err("User not associated with organization.")
    
    if not user:
        return err("No logged-in user found.")

    try:
        from django.utils.dateparse import parse_date
        import dateparser
        
        start_date = start_date.strip() if start_date else ""
        end_date = end_date.strip() if end_date else ""

        if not end_date:
            end_date = start_date

        # Try strict ISO parsing first
        s_date = parse_date(start_date)
        e_date = parse_date(end_date)
        
        # Fallback to smart parsing
        if not s_date:
            dt = dateparser.parse(start_date, settings={'PREFER_DATES_FROM': 'future'}, languages=['en'])
            if dt: s_date = dt.date()
            
        if not e_date:
            dt = dateparser.parse(end_date, settings={'PREFER_DATES_FROM': 'future'}, languages=['en'])
            if dt: e_date = dt.date()
        
        if not s_date or not e_date:
            return err(f"Could not understand the dates provided ('{start_date}' to '{end_date}'). Please use YYYY-MM-DD.")
            
        leave = LeaveRequest.objects.create(
            organization=org,
            employee=user,
            start_date=s_date,
            end_date=e_date,
            leave_type=leave_type,
            # reason is not stored effectively in current DB schema
            status="pending"
        )
        
        return ok(f"I have submitted your {leave_type} leave request from {s_date} to {e_date}.", id=leave.id)
        
    except Exception as e:
        return err(f"Failed to submit leave request: {e}")
