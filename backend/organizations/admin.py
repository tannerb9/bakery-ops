from django.contrib import admin

from organizations.models import Membership, Organization


class MembershipInline(admin.TabularInline[Membership, Organization]):
    model = Membership
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin[Organization]):
    list_display = ["name", "created_at"]
    inlines = [MembershipInline]
