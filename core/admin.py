from django.contrib import admin
from .models import Organization
# Register your models here.
admin.site.site_header = "Harvey Admin Panel"
admin.site.index_title = "Harvey Administration"
admin.site.site_title = "Harvey Admin"
admin.site.register(Organization)  # Unregister LogEntry for cleaner admin interface