import json
import os
from dataclasses import asdict

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from sdc_core.agent import checks, kit, project_map, runner

# Directories that never hold project code (for the list of changed files)
_SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.sdc_agent', 'static', 'www', 'media', '.idea', '.venv'}


class Command(BaseCommand):
    help = ('Compact project information and safe shortcuts for AI coding agents and scripts: overview, where, '
            'check, new-controller, new-model, test, build, kit. Never asks for input; paths are relative to the '
            'project.')
    # Django's system check warnings (e.g. a missing node_modules) would precede every answer; `check` covers SDC
    requires_system_checks = []

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action', required=True, metavar='ACTION')
        p = sub.add_parser('overview', help='apps, controllers and models of the project, one line each')
        p.add_argument('--app', help='only this app')
        p.add_argument('--all', action='store_true', help='also the controllers of installed apps (sdc_tools, ...)')
        p.add_argument('--json', action='store_true')
        p = sub.add_parser('where', help='all files of a controller (tag or snake_case name) or model')
        p.add_argument('name')
        p.add_argument('--json', action='store_true')
        p = sub.add_parser('check', help='consistency problems with their fixes (exit code 1 if any)')
        p.add_argument('--strict', action='store_true', help='missing documentation fails as well')
        p.add_argument('--json', action='store_true')
        p = sub.add_parser('new-controller', help='create a controller pair with view, URL, template, JS, SCSS')
        p.add_argument('app')
        p.add_argument('name', help='snake_case, e.g. book_list for <book-list>')
        p.add_argument('--mixins', default='', help='comma-separated mixin controllers, e.g. sdc_auto_submit')
        p = sub.add_parser('new-model', help='create an SdcModel with forms and templates')
        p.add_argument('app')
        p.add_argument('name', help='CamelCase class name')
        p = sub.add_parser('test', help='run the tests and print only a summary (full log in .sdc_agent/logs)')
        p.add_argument('--js', action='store_true', help='Jest tests (yarn/npm run sdc_test) instead of Django')
        p.add_argument('--all', action='store_true', help='Django and Jest tests')
        p.add_argument('test_args', nargs='*', metavar='ARG', help='passed to the test runner, e.g. a test label')
        p = sub.add_parser('build', help='build the assets and print only errors (full log in .sdc_agent/logs)')
        p.add_argument('--develop', action='store_true', help='development build (default: production)')
        p = sub.add_parser('kit', help='AGENTS.md and the skills for AI agents: install, update or check them')
        p.add_argument('kit_action', choices=['install', 'update', 'check'])
        p.add_argument('--force', action='store_true', help='install: overwrite existing files')

    def handle(self, *args, **opts):
        action = opts['action'].replace('-', '_')
        return getattr(self, f'_{action}')(opts)

    # ------------------------------------------------------------------ information
    def _map(self):
        return project_map.build()

    def _overview(self, opts):
        project = self._map()
        if opts['json']:
            self.stdout.write(json.dumps({'root': project.root,
                                          'controllers': [asdict(c) for c in project.controllers],
                                          'models': [asdict(m) for m in project.models]}, indent=1, default=str))
            return
        rel = project.rel
        apps = [opts['app']] if opts['app'] else project.project_apps()
        library = project.library_apps()
        lines = [f'SDC project {project.root}']
        if library and not opts['all']:
            lines.append('installed apps (not shown, --all): ' + ', '.join(f'{a} ({n} controllers)'
                                                                          for a, n in library.items()))
        for app in apps + (list(library) if opts['all'] else []):
            controllers = [c for c in project.controllers if c.app == app]
            models = [m for m in project.models if m.app == app]
            clients = [d for a, d in project.orphan_js if a == app]
            lines.append(f'app {app}')
            for c in controllers:
                js_dir = rel(os.path.dirname(c.js)) + '/' if c.js else 'no JS'
                lines.append(f'  <{c.tag}>  {c.url}  view {rel(c.view_file)}:{c.view_line}  js {js_dir}')
            for directory in clients:
                lines.append(f'  <{os.path.basename(directory).replace("_", "-")}>  client-only  {rel(directory)}/')
            for m in models:
                flags = ', '.join(sorted(m.forms)) or 'no forms'
                lines.append(f'  model {m.name}({", ".join(m.fields)})  {rel(m.file)}:{m.line}  forms: {flags}'
                             + ('' if m.mcp else '  mcp: hidden'))
            if not (controllers or models or clients):
                lines.append('  (no SDC controllers or models)')
        problems = [p for p in checks.run_checks(project) if p.severity != 'doc']
        lines.append(f'{len(problems)} problem(s)' + (' — run: python manage.py sdc_agent check' if problems else ''))
        self.stdout.write('\n'.join(lines))

    def _where(self, opts):
        project = self._map()
        controllers, models = project.find(opts['name'])
        if not controllers and not models:
            raise CommandError(f"No controller or model '{opts['name']}'. List them with: "
                               f"python manage.py sdc_agent overview")
        if opts['json']:
            self.stdout.write(json.dumps({'controllers': [asdict(c) for c in controllers],
                                          'models': [asdict(m) for m in models]}, indent=1, default=str))
            return
        rel = project.rel
        lines = []
        for c in controllers:
            lines += [f'<{c.tag}> (app {c.app})',
                      f'  view       {rel(c.view_file)}:{c.view_line}  class {c.view_class.rsplit(".", 1)[-1]}',
                      f'  url        {c.url}',
                      f'  template   {rel(c.template) if c.template else (c.template_name or "-")}',
                      f'  js         {rel(c.js)}',
                      f'  scss       {rel(c.scss)}',
                      f'  organizer  {rel(c.organizer)}' + (f':{c.organizer_line}' if c.organizer_line
                                                            else '  (not imported!)')]
            tests = os.path.join(os.path.dirname(os.path.dirname(c.organizer or '')), '..', 'tests',
                                 f'{c.app}.test.js') if c.organizer else None
            if tests and os.path.isfile(tests):
                lines.append(f'  js tests   {rel(os.path.normpath(tests))}')
        for m in models:
            lines += [f'model {m.name} (app {m.app})',
                      f'  class      {rel(m.file)}:{m.line}',
                      f'  fields     {", ".join(m.fields)}']
            for key, path in sorted(m.forms.items()):
                lines.append(f'  form {key:<6} {path}')
            lines.append(f'  js model   {rel(m.js_dir)}' + ('' if m.mcp else '\n  mcp        hidden (SdcMeta.mcp)'))
        self.stdout.write('\n'.join(lines))

    def _check(self, opts):
        project = self._map()
        problems = checks.run_checks(project)
        failing = [p for p in problems if opts['strict'] or p.severity != 'doc']
        if opts['json']:
            self.stdout.write(json.dumps([asdict(p) for p in problems], indent=1))
        else:
            for p in problems:
                location = f'{project.rel(p.file)}:{p.line}' if p.line else project.rel(p.file)
                self.stdout.write(f'{p.severity:<7} {location}  {p.message}\n        fix: {p.fix}')
            docs = len(problems) - len([p for p in problems if p.severity != 'doc'])
            self.stdout.write(f'{len(problems) - docs} problem(s), {docs} missing documentation')
        if failing:
            raise SystemExit(1)

    # ------------------------------------------------------------------ scaffolding
    def _files(self, root):
        state = {}
        for directory, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for name in files:
                path = os.path.join(directory, name)
                try:
                    state[path] = os.lstat(path).st_mtime_ns
                except OSError:
                    pass
        return state

    def _report_changes(self, root, before, next_steps):
        after = self._files(root)
        added = sorted(p for p in after if p not in before)
        changed = sorted(p for p in after if p in before and after[p] != before[p])
        lines = [f'  + {os.path.relpath(p, root)}' for p in added] + \
                [f'  ~ {os.path.relpath(p, root)}' for p in changed]
        self.stdout.write('\n'.join(['Created (+) and changed (~) files:'] + lines + ['Next:'] +
                                    [f'  - {step}' for step in next_steps]))

    def _new_controller(self, opts):
        from django.conf import settings
        root = str(settings.BASE_DIR)
        before = self._files(root)
        call_command('sdc_cc', app_name=opts['app'], controller_name=opts['name'],
                     mixin_apps=opts['mixins'] or True, stdout=open(os.devnull, 'w'))
        tag = opts['name'].replace('_', '-')
        self._report_changes(root, before, [
            f'server: edit the view class in {opts["app"]}/sdc_views.py (get_content renders the template; '
            f'server calls are methods `def name(self, channel, **kwargs)`)',
            f'html: {opts["app"]}/templates/{opts["app"]}/sdc/{opts["name"]}.html',
            f'client: {opts["app"]}/Assets/src/{opts["app"]}/controller/{opts["name"]}/{opts["name"]}.js; event '
            f'handlers as methods (sdc_click="method") or plain functions, not arrow functions in the constructor',
            f'use it with <{tag}></{tag}> or the URL /~{tag}; rebuild the assets (sdc_agent build)',
        ])

    def _new_model(self, opts):
        from django.conf import settings
        root = str(settings.BASE_DIR)
        before = self._files(root)
        call_command('sdc_new_model', app_name=opts['app'], model_name=opts['name'], stdout=open(os.devnull, 'w'))
        self._report_changes(root, before, [
            f'add the fields to class {opts["name"]} in {opts["app"]}/models.py and adapt is_authorised / '
            f'get_queryset (who may load, create, save, delete)',
            'python manage.py makemigrations && python manage.py migrate',
            f'forms: {opts["app"]}/forms.py (SdcMeta.create_form / edit_form)',
        ])

    # ------------------------------------------------------------------ tests and build
    def _write_result(self, result):
        lines = [f'{result.name}: {"ok" if result.ok else "FAILED"}  {result.summary}']
        for failure in result.failures[:runner.MAX_FAILURES]:
            lines.append('  ' + failure)
        if len(result.failures) > runner.MAX_FAILURES:
            lines.append(f'  … {len(result.failures) - runner.MAX_FAILURES} more')
        lines.append(f'  full log: {os.path.relpath(result.log)}')
        self.stdout.write('\n'.join(lines))

    def _test(self, opts):
        from django.conf import settings
        root = str(settings.BASE_DIR)
        results = []
        if not opts['js'] or opts['all']:
            results.append(runner.run_python_tests(root, opts['test_args'] if not opts['js'] else ()))
        if opts['js'] or opts['all']:
            results.append(runner.run_js_tests(root, opts['test_args'] if opts['js'] and not opts['all'] else ()))
        for result in results:
            self._write_result(result)
        if not all(r.ok for r in results):
            raise SystemExit(1)

    def _build(self, opts):
        from django.conf import settings
        result = runner.run_build(str(settings.BASE_DIR), 'develop' if opts['develop'] else 'build')
        self._write_result(result)
        if not result.ok:
            raise SystemExit(1)

    # ------------------------------------------------------------------ agent kit
    def _kit(self, opts):
        from django.conf import settings
        root = str(settings.BASE_DIR)
        action = opts['kit_action']
        if action == 'check':
            state = kit.status(root)
            if not state['installed']:
                self.stdout.write('agent kit: not installed (python manage.py sdc_agent kit install)')
                raise SystemExit(1)
            problems = [f'outdated: {f}' for f in state['outdated']] + [f'missing: {f}' for f in state['missing']]
            for line in problems + [f'edited (kept on update): {f}' for f in state['edited']]:
                self.stdout.write(line)
            self.stdout.write('agent kit: ' + ('run python manage.py sdc_agent kit update' if problems
                                               else 'up to date'))
            if problems:
                raise SystemExit(1)
            return
        project = self._map()
        if action == 'install':
            if kit.load_manifest(root) is not None and not opts['force']:
                raise CommandError('The agent kit is installed already: use `sdc_agent kit update` '
                                   '(or `kit install --force` to overwrite edited files)')
            result = kit.install(root, project, force=opts['force'])
        else:
            result = kit.update(root, project)
        for name in result.written:
            self.stdout.write(f'  wrote {name}')
        for name in result.kept:
            self.stdout.write(f'  kept  {name} (edited in the project)')
        self.stdout.write(f'agent kit {action}: {len(result.written)} written, {len(result.kept)} kept, '
                          f'{len(result.unchanged)} unchanged')
