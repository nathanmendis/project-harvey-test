def is_org_admin(user):
    return user.is_authenticated and (user.role == "org_admin" or user.is_superuser)

def is_hr_or_manager(user):
    return user.is_authenticated and (user.role == "hr" or user.role == "manager")

def is_admin_manager_hr(user):
    return user.is_authenticated and (user.role in ["org_admin", "hr", "manager"] or user.is_superuser)

