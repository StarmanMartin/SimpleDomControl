import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from sdc_core import api_tokens
from sdc_core.mcp.settings import mcp_settings, server_name

TOKEN_VARIABLE = 'SDC_MCP_TOKEN'


class Command(BaseCommand):
    help = ("Prints how to connect an MCP client (Claude Code, Claude Desktop, Cursor, ...) to the MCP endpoint of "
            "this project: a 'claude mcp add' command and an .mcp.json entry. With --user it also creates the API "
            "token (shown once).")

    def add_arguments(self, parser):
        parser.add_argument('--url', help='URL of the site (default: settings.HOME_URL)')
        parser.add_argument('--name', help='Name of the server in the client (default: SDC_MCP["name"] or the '
                                           'project directory)')
        parser.add_argument('--user', help='Create a token for this username')
        parser.add_argument('--privileges', default='read',
                            help='Privileges of the new token: comma-separated or a preset (read, read_write, '
                                 'full); default: read')
        parser.add_argument('--days', type=int, help='Lifetime of the new token in days')

    def handle(self, *args, **opts):
        url = (opts['url'] or getattr(settings, 'HOME_URL', '') or 'http://127.0.0.1:8000').rstrip('/') + \
            '/sdc_mcp/'
        name = opts['name'] or server_name()
        name = ''.join(c if c.isalnum() or c in '-_' else '-' for c in name)
        if not mcp_settings()['enabled']:
            self.stderr.write(self.style.WARNING(
                "SDC_MCP['enabled'] is False: the endpoint answers 404 until you enable it in settings.py."))

        token = None
        if opts['user']:
            token = self._create_token(opts)
        shown = token or 'sdc_...'

        self.stdout.write('\nClaude Code (run in your project):\n')
        self.stdout.write(f'  claude mcp add --transport http {name} {url} '
                          f'--header "Authorization: Bearer {shown}"\n')
        self.stdout.write(f'\n.mcp.json (keep the token out of the file: set {TOKEN_VARIABLE} in your environment):\n')
        entry = {'mcpServers': {name: {'type': 'http', 'url': url,
                                       'headers': {'Authorization': f'Bearer ${{{TOKEN_VARIABLE}}}'}}}}
        self.stdout.write(json.dumps(entry, indent=2) + '\n')
        if token:
            self.stdout.write(f'\n  export {TOKEN_VARIABLE}={token}\n')
            self.stdout.write(self.style.WARNING('\nThe token is shown only now. Revoke it in <sdc-api-tokens> or '
                                                 'with manage.py sdc_tokens revoke when you no longer need it.\n'))
        else:
            self.stdout.write('\nCreate the token in the web app ("API tokens") or run this command again with '
                              '--user <username>.\n')

    def _create_token(self, opts):
        user = get_user_model().objects.filter(username=opts['user']).first()
        if user is None:
            raise CommandError(f"No user {opts['user']}")
        value = opts['privileges'].strip()
        privileges = list(api_tokens.PRESETS[value]) if value in api_tokens.PRESETS else \
            [p for p in value.split(',') if p.strip()]
        expiry = {}
        if opts['days'] is not None:
            import datetime
            from django.utils import timezone
            expiry['expires_at'] = timezone.now() + datetime.timedelta(days=opts['days'])
        try:
            _token, secret = api_tokens.create_token(user, f'MCP {opts["name"] or server_name()}', privileges,
                                                     **expiry)
        except api_tokens.TokenError as e:
            raise CommandError(str(e))
        return secret
