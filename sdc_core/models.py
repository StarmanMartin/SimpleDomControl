import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ApiToken(models.Model):
    """
    A token for the REST API (``sdc_api/``) and the MCP endpoint, created by a user for one client.

    - Only the SHA-256 hash of the token is stored; the token itself is shown once when it is created.
    - ``prefix`` (the first characters of the token) identifies it in lists without revealing it.
    - ``privileges`` (see ``sdc_core.api_tokens``) narrow what the token may do: a token never has more rights
      than its user.
    - A token stops working when it expires, when it is revoked (``revoked_at``; revoking also revokes the tokens
      it created) or when its user is deactivated. Revoked tokens stay in the list as history.
    """
    KIND_PERSONAL = 'personal'
    KIND_LOGIN = 'login'
    KINDS = ((KIND_PERSONAL, 'Personal token'), (KIND_LOGIN, 'Login (username and password)'))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sdc_api_tokens')
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=KINDS, default=KIND_PERSONAL)
    prefix = models.CharField(max_length=16, editable=False)
    secret_hash = models.CharField(max_length=64, unique=True, editable=False)
    privileges = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+')
    created_by_token = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='created_tokens')

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'API token'

    def __str__(self):
        return f'{self.name} ({self.prefix}…)'

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def is_valid(self):
        return not self.is_revoked and not self.is_expired and self.user.is_active

    def revoke(self, by=None):
        """Revokes this token and every token created with it (recursively); revoked tokens keep their date."""
        now = timezone.now()
        pending, seen = [self.pk], set()
        while pending:
            seen.update(pending)
            ApiToken.objects.filter(pk__in=pending, revoked_at__isnull=True).update(revoked_at=now, revoked_by=by)
            pending = list(ApiToken.objects.filter(created_by_token__in=pending).exclude(pk__in=seen)
                           .values_list('pk', flat=True))
        self.refresh_from_db(fields=['revoked_at', 'revoked_by'])
