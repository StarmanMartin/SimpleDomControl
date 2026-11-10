from django.contrib import admin

from sdc_core.models import ApiToken


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    """API tokens of all users: list, filter and revoke them. The secret is never stored, so it cannot be shown."""
    list_display = ('name', 'prefix', 'user', 'kind', 'created_at', 'expires_at', 'last_used_at', 'revoked_at')
    list_filter = ('kind', 'revoked_at')
    search_fields = ('name', 'prefix', 'user__username')
    readonly_fields = ('id', 'user', 'kind', 'prefix', 'privileges', 'created_at', 'expires_at', 'last_used_at',
                       'last_used_ip', 'revoked_at', 'revoked_by', 'created_by_token')
    exclude = ('secret_hash',)
    actions = ('revoke',)

    def has_add_permission(self, request):
        # Tokens are created by their users (or with manage.py sdc_tokens): the secret is shown only then
        return False

    @admin.action(description='Revoke the selected tokens (and the tokens they created)')
    def revoke(self, request, queryset):
        for token in queryset.filter(revoked_at__isnull=True):
            token.revoke(by=request.user)
