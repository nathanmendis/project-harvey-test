from langchain_core.tools import tool
from core.models.recruitment import JobRole
from core.ai.agentic.tools.utils import ok, err, get_org

@tool("create_job_description", return_direct=True)
def create_job_description(title: str, description: str, requirements: str, department: str, user=None) -> str:
    """Creates a job posting / role for hiring."""
    org = get_org(user)
    if not org:
        return err("User is not associated with any organization. Please contact support.")

    j = JobRole.objects.create(
        organization=org,
        title=title,
        description=description,
        requirements=requirements,
        department=department,
    )
    return ok(f"I've created the new job role for '{title}' in the {department} department.", id=j.id, title=title)


@tool("list_job_roles", return_direct=True)
def list_job_roles(department: str = "", title: str = "", user=None) -> str:
    """Lists available job roles/openings."""
    org = get_org(user)
    if not org:
        return err("User not in organization.")

    jobs = JobRole.objects.filter(organization=org)
    
    if department:
        jobs = jobs.filter(department__icontains=department)
    if title:
        jobs = jobs.filter(title__icontains=title)

    if not jobs.exists():
        return ok("No job roles found.")

    results = []
    lines = [f"Here are the job roles for {org.name}:"]
    
    for j in jobs:
        lines.append(f"• **{j.title}** ({j.department})")
        results.append({"id": j.id, "title": j.title, "department": j.department})

    return ok("\n".join(lines), results=results)


@tool("get_job_role_detail", return_direct=True)
def get_job_role_detail(job_id: int, user=None) -> str:
    """Gets details for a specific job role."""
    org = get_org(user)
    if not org:
        return err("User not in organization.")

    j = JobRole.objects.filter(organization=org, id=job_id).first()
    if not j:
        return err(f"Job role with ID {job_id} not found.")

    detail = [
        f"**Job Role: {j.title}**",
        f"🏢 Department: {j.department}",
        f"\n**Description**:\n{j.description}",
        f"\n**Requirements**:\n{j.requirements}"
    ]

    return ok("\n".join(detail), id=j.id, title=j.title)
