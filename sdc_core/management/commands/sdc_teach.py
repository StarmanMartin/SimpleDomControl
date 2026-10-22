import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import URLPattern, URLResolver, get_resolver

from sdc_core.management.commands.init_add import options
from sdc_core.management.commands.init_add.utils import convert_to_tag_name
from sdc_core.management.commands.utils.teach_crawler import Crawler, merge_crawls
from sdc_core.management.commands.utils.teach_markdown import render_skill

SESSION_SCRIPT = """
import json, os
from importlib import import_module
from django.conf import settings
from django.contrib.auth import authenticate, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
user = authenticate(username=os.environ['SDC_TEACH_USER'], password=os.environ['SDC_TEACH_PASSWORD'])
if user is None:
    print(json.dumps({'error': 'invalid credentials'}))
else:
    s = import_module(settings.SESSION_ENGINE).SessionStore()
    s[SESSION_KEY] = str(user.pk)
    s[BACKEND_SESSION_KEY] = user.backend
    s[HASH_SESSION_KEY] = user.get_session_auth_hash()
    s.create()
    print(json.dumps({'name': settings.SESSION_COOKIE_NAME, 'value': s.session_key}))
"""


class Command(BaseCommand):
    help = ("Crawls the SDC app in a headless browser (follows every navigation link, clicks every "
            "non-destructive button) and writes a Markdown skill file describing the UI for AI agents.")

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', type=str, default=None,
                            help='Markdown output file (default: <project>/SDC_SKILL.md)')
        parser.add_argument('--port', type=int, default=0, help='Port of the crawl server (default: a free port)')
        parser.add_argument('--start', type=str, default='/', help='Start path of the crawl')
        parser.add_argument('--database', type=str, default='jest',
                            help='DJANGO_DATABASE alias used by the crawl server (default: jest, never your dev DB)')
        parser.add_argument('--fixture', type=str, default=None, help='Fixture loaded with loaddata before crawling')
        parser.add_argument('--max-depth', type=int, default=5, help='Maximum navigation depth')
        parser.add_argument('--max-nodes', type=int, default=200, help='Maximum number of views')
        parser.add_argument('--user', type=str, default=None, help='Additionally crawl logged in as this user')
        parser.add_argument('--password', type=str, default=None, help='Password of --user')
        parser.add_argument('--no-click', action='store_true', help='Only follow links, do not click buttons')
        parser.add_argument('--click-all', action='store_true',
                            help='Also click buttons matching the denylist (delete, logout, submit, ...)')
        parser.add_argument('--deny', type=str, default=None,
                            help='Additional regex of button texts/handlers that must not be clicked')
        parser.add_argument('--browser-path', type=str, default=None, help='Chromium/Chrome executable')
        parser.add_argument('--headed', action='store_true', help='Show the browser window')
        parser.add_argument('--timeout', type=int, default=10000, help='Timeout per page action in ms')
        parser.add_argument('--no-ask', action='store_true',
                            help='Do not open a browser window asking you to fill in forms '
                                 '(default: ask when running in a terminal with a display)')

    def handle(self, *args, **ops):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise CommandError('playwright is not installed: pip install playwright && playwright install chromium')

        project = getattr(options, 'PROJECT', None)
        if not project or project == 'Undefined':
            project = settings.ROOT_URLCONF.split('.')[0]
        output = ops['output'] or os.path.join(options.PROJECT_ROOT, 'SDC_SKILL.md')
        if ops['user'] and ops['password'] is None:
            raise CommandError('--user requires --password')

        if ops['database'] not in getattr(settings, 'DATABASES_AVAILABLE', {ops['database']: None}):
            raise CommandError(f"DJANGO_DATABASE alias '{ops['database']}' is not defined in your settings")
        env = os.environ | {'DJANGO_DATABASE': ops['database']}
        self._manage(env, 'migrate', '--noinput')
        if ops['fixture']:
            self._manage(env, 'loaddata', ops['fixture'])

        port = ops['port'] or self._free_port()
        base_url = f'http://127.0.0.1:{port}'
        # The server log goes to a file: an unread pipe fills up and blocks the server.
        server_log = tempfile.TemporaryFile(mode='w+')
        server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'],
                                  env=env, stdout=server_log, stderr=subprocess.STDOUT, text=True)
        try:
            self._wait_for_server(server, server_log, base_url)
            self.stdout.write(self.style.SUCCESS(f'Crawl server running on {base_url} (DB: {ops["database"]})'))
            cookie = self._login_cookie(env, ops) if ops['user'] else None
            with sync_playwright() as p:
                browser = self._launch(p, ops, headless=not ops['headed'])
                headed = []

                def ask_browser():
                    # The headed window for manual form input is opened on first use only
                    if not headed:
                        try:
                            headed.append(self._launch(p, ops, headless=False))
                        except CommandError as e:
                            self.stderr.write(f'Cannot open a browser window for form input: {e}')
                            headed.append(None)
                    return headed[0]

                try:
                    tree, crawled_as = self._crawl(browser, base_url, cookie, ops,
                                                   ask_browser if self._can_ask(ops) else None)
                finally:
                    browser.close()
                    if headed and headed[0]:
                        headed[0].close()
        finally:
            server.terminate()
            try:
                server.wait(10)
            except subprocess.TimeoutExpired:
                server.kill()
            server_log.close()

        markdown = render_skill(tree, {
            'project': project,
            'crawled_as': crawled_as,
            'logged_in_label': f'user {ops["user"]}',
            'controller_infos': self._controller_infos(),
        })
        with open(output, 'w') as f:
            f.write(markdown)
        self.stdout.write(self.style.SUCCESS(
            f'Wrote {output}: {len(tree["nodes"])} views, {len(tree["errors"])} errors observed'))

    # --------------------------------------------------------------- crawl
    def _crawl(self, browser, base_url, cookie, ops, ask_browser):
        kwargs = dict(start=ops['start'], max_depth=ops['max_depth'], max_nodes=ops['max_nodes'],
                      click=not ops['no_click'], click_all=ops['click_all'], deny=ops['deny'],
                      timeout=ops['timeout'], log=self.stdout.write,
                      ask_browser=ask_browser, form_cache={})

        context = browser.new_context()
        anonymous = Crawler(context, base_url, label='anonymous', **kwargs)
        tree = anonymous.crawl()
        context.close()
        crawled_as = ['anonymous']
        if cookie:
            context = browser.new_context()
            context.add_cookies([{'name': cookie['name'], 'value': cookie['value'], 'url': base_url}])
            logged_in = Crawler(context, base_url, label=f'user {ops["user"]}', **kwargs)
            logged_in_tree = logged_in.crawl()
            context.close()
            tree = merge_crawls(tree, logged_in_tree)
            crawled_as.append(f'user {ops["user"]}')
        return tree, crawled_as

    @staticmethod
    def _can_ask(ops):
        has_display = sys.platform in ('darwin', 'win32') or os.environ.get('DISPLAY') or os.environ.get(
            'WAYLAND_DISPLAY')
        return not ops['no_ask'] and sys.stdin.isatty() and bool(has_display)

    @staticmethod
    def _launch(p, ops, headless):
        launch = dict(headless=headless)
        if ops['browser_path']:
            return p.chromium.launch(executable_path=ops['browser_path'], **launch)
        try:
            return p.chromium.launch(**launch)
        except Exception:  # noqa: BLE001 - fall back to an installed Google Chrome
            try:
                return p.chromium.launch(channel='chrome', **launch)
            except Exception as e:
                raise CommandError(f'No browser found ({str(e).splitlines()[0]}). '
                                   f'Run "playwright install chromium" or pass --browser-path.')

    # -------------------------------------------------------------- server
    @staticmethod
    def _manage(env, *cmd):
        res = subprocess.run([sys.executable, 'manage.py', *cmd], env=env, capture_output=True, text=True)
        if res.returncode != 0:
            raise CommandError(f'manage.py {" ".join(cmd)} failed:\n{res.stderr}')
        return res.stdout

    @staticmethod
    def _free_port():
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    @staticmethod
    def _wait_for_server(server, server_log, base_url, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if server.poll() is not None:
                server_log.seek(0)
                raise CommandError(f'Crawl server stopped:\n{server_log.read()[-5000:]}')
            try:
                urllib.request.urlopen(base_url, timeout=2)
                return
            except urllib.error.HTTPError:
                return
            except OSError:
                time.sleep(0.3)
        raise CommandError(f'Crawl server did not start within {timeout}s')

    def _login_cookie(self, env, ops):
        out = self._manage(env | {'SDC_TEACH_USER': ops['user'], 'SDC_TEACH_PASSWORD': ops['password']},
                           'shell', '-c', SESSION_SCRIPT)
        cookie = json.loads(out.strip().splitlines()[-1])
        if 'error' in cookie:
            raise CommandError(f'Login as {ops["user"]} failed: {cookie["error"]} (DB: {ops["database"]})')
        return cookie

    # ---------------------------------------------------------- controllers
    @staticmethod
    def _controller_infos():
        infos = {}

        def walk(patterns, prefix):
            for p in patterns:
                if isinstance(p, URLResolver):
                    walk(p.url_patterns, prefix + str(p.pattern))
                elif isinstance(p, URLPattern) and (p.name or '').startswith('scd_view_'):
                    view = getattr(p.callback, 'view_class', None)
                    if view is None:
                        continue
                    tag = convert_to_tag_name(view.__name__)
                    infos[tag] = {
                        'app': view.__module__.split('.')[0],
                        'view_class': f'{view.__module__}.{view.__name__}',
                        'url': '/' + prefix + str(p.pattern),
                    }

        walk(get_resolver().url_patterns, '')
        return infos
