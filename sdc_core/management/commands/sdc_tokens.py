import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from sdc_core import api_tokens


class Command(BaseCommand):
    help = ("Lists, creates and revokes API tokens of the REST API and MCP endpoint. "
            "Privileges: model:<Name|*>:<read|write|delete>, account:read, account:write, account:tokens, "
            "or a preset (read, read_write, full).")

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action', required=True)
        list_parser = sub.add_parser('list', help='List tokens')
        list_parser.add_argument('--user', help='Only the tokens of this username')
        list_parser.add_argument('--all', action='store_true', help='Also revoked and expired tokens')

        create = sub.add_parser('create', help='Create a token and print it once')
        create.add_argument('--user', required=True, help='Username of the token owner')
        create.add_argument('--name', required=True, help='Name of the token, e.g. the client using it')
        create.add_argument('--privileges', default='read',
                            help='Comma-separated privileges or a preset (read, read_write, full); default: read')
        create.add_argument('--days', type=int, default=None,
                            help='Lifetime in days (default: SDC_API_TOKENS["default_lifetime_days"])')

        revoke = sub.add_parser('revoke', help='Revoke a token (and the tokens it created)')
        revoke.add_argument('token', help='Id or shown prefix of the token')

    def handle(self, *args, **opts):
        return getattr(self, f"_{opts['action']}")(opts)

    def _list(self, opts):
        from sdc_core.models import ApiToken
        tokens = ApiToken.objects.select_related('user')
        if opts['user']:
            tokens = tokens.filter(user__username=opts['user'])
        for token in tokens:
            if not opts['all'] and not token.is_valid:
                continue
            state = 'revoked' if token.is_revoked else 'expired' if token.is_expired else 'valid'
            expires = token.expires_at.isoformat(timespec='minutes') if token.expires_at else 'never'
            self.stdout.write(f"{token.id}  {token.prefix}…  {token.user.username:<15} {token.name:<25} "
                              f"{state:<8} expires {expires}  {', '.join(token.privileges)}")

    def _create(self, opts):
        user = get_user_model().objects.filter(username=opts['user']).first()
        if user is None:
            raise CommandError(f"No user {opts['user']}")
        privileges = opts['privileges'].strip()
        privileges = list(api_tokens.PRESETS[privileges]) if privileges in api_tokens.PRESETS else \
            [p for p in privileges.split(',') if p.strip()]
        expiry = {}
        if opts['days'] is not None:
            expiry['expires_at'] = timezone.now() + datetime.timedelta(days=opts['days'])
        try:
            token, secret = api_tokens.create_token(user, opts['name'], privileges, **expiry)
        except api_tokens.TokenError as e:
            raise CommandError(str(e))
        self.stdout.write(f"Token {token.id} for {user.username} ({', '.join(token.privileges)}), "
                          f"expires {token.expires_at.isoformat(timespec='minutes') if token.expires_at else 'never'}")
        self.stdout.write('It is shown only now:')
        self.stdout.write(secret)

    def _revoke(self, opts):
        from sdc_core.models import ApiToken
        value = opts['token'].rstrip('…')
        tokens = ApiToken.objects.filter(prefix=value)
        if not tokens.exists():
            try:
                tokens = ApiToken.objects.filter(pk=value)
                tokens.exists()
            except Exception:
                tokens = ApiToken.objects.none()
        if tokens.count() != 1:
            raise CommandError(f'No unique token {value}')
        token = tokens.get()
        token.revoke()
        self.stdout.write(f'Revoked {token}')
