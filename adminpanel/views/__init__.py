from .utils import is_org_admin
from .dashboard import admin_dashboard
from .employees import (
    add_employee,
    manage_employees,
    remove_employee,
    toggle_chat_access,
    toggle_admin_role,
    search_employee
)
from .admins import add_org_admin, manage_org_admins
from .policies import (
    manage_policies,
    add_policy,
    reindex_policy,
    delete_policy
)
from .invites import invite_user, manage_invites, delete_invite
from .settings import org_settings
from .recruitment import (
    recruitment_dashboard,
    candidates,
    add_candidate,
    candidate_detail,
    jobs,
    add_job,
    job_detail,
    interviews,
    interview_detail
)
from .leaves import (
    leaves,
    leave_detail,
    approve_leave
)
