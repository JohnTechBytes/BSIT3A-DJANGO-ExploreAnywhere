"""Moderate visitor check-ins. Approval requires external corroboration by staff."""
from django.contrib import admin
from django.utils import timezone
from .models import VisitCheckIn


@admin.register(VisitCheckIn)
class VisitCheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'place', 'visited_on', 'status', 'submitted_at', 'reviewed_by')
    list_filter = ('status', 'visited_on')
    search_fields = ('user__username', 'place__title', 'visit_note')
    list_select_related = ('user', 'place', 'reviewed_by')
    readonly_fields = (
        'user', 'place', 'visited_on', 'visit_note', 'status',
        'submitted_at', 'reviewed_at', 'reviewed_by',
    )
    actions = ('approve_reviewed', 'reject_reviewed', 'revoke_approval')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(place__city_id=2)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Approve independently corroborated pending check-ins', permissions=['change'])
    def approve_reviewed(self, request, queryset):
        # Staff must first write >=20 characters explaining independent
        # corroboration in reviewer_note on each check-in's admin detail page.
        eligible = [entry.pk for entry in queryset.filter(
            status=VisitCheckIn.Status.PENDING, place__city_id=2
        ) if len(entry.reviewer_note.strip()) >= 20]
        count = VisitCheckIn.objects.filter(pk__in=eligible,
            status=VisitCheckIn.Status.PENDING, place__city_id=2).update(
            status=VisitCheckIn.Status.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request,
            f'Approved {count} check-in(s). Others need a 20+ character reviewer note describing independent corroboration.')

    @admin.action(description='Reject pending check-ins', permissions=['change'])
    def reject_reviewed(self, request, queryset):
        count = queryset.filter(status=VisitCheckIn.Status.PENDING, place__city_id=2).update(
            status=VisitCheckIn.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'Rejected {count} pending check-in(s).')

    @admin.action(description='Revoke previously approved check-ins', permissions=['change'])
    def revoke_approval(self, request, queryset):
        # If evidence is later invalidated, rewards disappear automatically.
        count = queryset.filter(status=VisitCheckIn.Status.APPROVED, place__city_id=2).update(
            status=VisitCheckIn.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'Revoked {count} approved check-in(s).')
