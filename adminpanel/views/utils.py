def is_org_admin(user):
    return user.is_authenticated and (user.role == "org_admin" or user.is_superuser)
