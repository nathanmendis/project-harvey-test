from langchain_core.tools import tool
from typing import Optional
from core.models.leaves import LeaveRequest, LeaveBalance
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
def apply_leave(start_date: str, end_date: str, leave_type: str, user=None) -> str:
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
            
        # Check balance
        days_requested = (e_date - s_date).days + 1
        year = s_date.year
        balance = LeaveBalance.objects.filter(employee=user, organization=org, year=year, leave_type__iexact=leave_type).first()
        
        if balance and balance.remaining < days_requested:
            return err(f"You only have {balance.remaining} days of {leave_type} leave remaining, but requested {days_requested} days.")

        leave = LeaveRequest.objects.create(
            organization=org,
            employee=user,
            start_date=s_date,
            end_date=e_date,
            leave_type=leave_type,
            status="pending"
        )
        
        return ok(f"I have submitted your {leave_type} leave request from {s_date} to {e_date}.", id=leave.id)
        
    except Exception as e:
        return err(f"Failed to submit leave request: {e}")

@tool("check_leave_balance", return_direct=True)
def check_leave_balance(leave_type: Optional[str] = None, year: Optional[int] = None, user=None) -> str:
    """
    Checks the user's remaining leave balance. Can filter by leave_type or year.
    year is an integer (e.g. 2026).
    leave_type is entirely optional (e.g., 'Sick', 'Annual', 'Casual').
    """
    org = get_org(user)
    if not user or not org:
        return err("User error.")
        
    from django.utils import timezone
    if year is None:
        year = timezone.now().year
        
    balances = LeaveBalance.objects.filter(employee=user, organization=org, year=year)
    if leave_type:
        balances = balances.filter(leave_type__iexact=leave_type)
        
    if not balances.exists():
        return ok(f"I couldn't find any leave balances recorded for you in {year}.")
        
    lines = [f"Here are your leave balances for {year}:"]
    for b in balances:
        lines.append(f"• **{b.leave_type}**: {b.remaining} days remaining (Total: {b.total_allocated}, Used: {b.used})")
        
    return ok("\n".join(lines))
