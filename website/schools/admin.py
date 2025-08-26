from django.contrib import admin
from .models import School, SchoolDomain


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "schema_name", "created_on")


@admin.register(SchoolDomain)
class SchoolDomainAdmin(admin.ModelAdmin):
    list_display = ("id", "domain", "tenant", "is_primary")
