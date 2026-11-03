import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from importlib.metadata import PackageNotFoundError, version

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sdc_core.management.commands.sdc_teach import Command as TeachCommand
from sdc_core.management.commands.utils.eval_ai import (
    JUDGE_PROMPT, EvalConfigError, check_episode, db_changes, episode_key, episode_metrics, format_table, load_tasks,
    outcome, parse_condition, parse_judge, parse_model, parse_users, prompt_for_run, prompt_warnings, read_results,
    settings_module_source, summarize, write_csv)
from sdc_core.management.commands.utils.teach_crawler import WAIT_READY_JS

# Run in the evaluation database (manage.py shell -c): optionally resets it from the fixtures, creates a session
# for each given user and prints a snapshot of all tables (row count and hash per model)
STATE_SCRIPT = """
import hashlib, json, os
from importlib import import_module
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.core.management import call_command
fixtures = json.loads(os.environ['SDC_EVAL_FIXTURES'])
if fixtures is not None:
    call_command('flush', interactive=False, verbosity=0)
    if fixtures:
        call_command('loaddata', *fixtures, verbosity=0)
sessions = {}
for role, u in json.loads(os.environ['SDC_EVAL_USERS']).items():
    user = authenticate(username=u['username'], password=u['password'])
    if user is None:
        sessions[role] = {'error': 'invalid credentials for ' + u['username']}
        continue
    s = import_module(settings.SESSION_ENGINE).SessionStore()
    s[SESSION_KEY] = str(user.pk)
    s[BACKEND_SESSION_KEY] = user.backend
    s[HASH_SESSION_KEY] = user.get_session_auth_hash()
    s.create()
    sessions[role] = {'name': settings.SESSION_COOKIE_NAME, 'value': s.session_key}
ignored = {'sessions.session', 'admin.logentry', 'contenttypes.contenttype', 'auth.permission'}
snapshot = {}
for model in apps.get_models():
    label = model._meta.label_lower
    if label in ignored or not model._meta.managed or model._meta.proxy:
        continue
    rows = list(model._base_manager.order_by('pk').values_list())
    snapshot[label] = [len(rows), hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()]
print('SDC_EVAL_STATE ' + json.dumps({'sessions': sessions, 'snapshot': snapshot}))
"""

# Records form submissions of the app (not of the assistant panel) and every error view (<sdc-error>, e.g. after
# navigating to a path that does not exist) shown in the page
SPY_JS = """
window.__sdcEvalSubmits = [];
window.__sdcEvalErrorViews = [];
document.addEventListener('submit', (e) => {
    const form = e.target;
    if (form && form.closest && !form.closest('sdc-ai-assistant')) {
        window.__sdcEvalSubmits.push(form.getAttribute('SdcModelName') || form.getAttribute('class') || 'form');
    }
}, true);
new MutationObserver((mutations) => {
    for (const m of mutations) {
        for (const node of m.addedNodes) {
            if (node.nodeType !== 1) continue;
            // The navigator inserts suffixed tags, e.g. <sdc-error_sdc-navigation-client data-code="404">
            const isError = (el) => el.tagName.startsWith('SDC-ERROR');
            const errors = [node, ...node.querySelectorAll('*')].filter(isError);
            for (const el of errors) {
                if (!el.closest('sdc-ai-assistant')) {
                    window.__sdcEvalErrorViews.push({path: location.pathname,
                        code: el.getAttribute('data-code') || el.getAttribute('code') || ''});
                }
            }
        }
    }
}).observe(document, {childList: true, subtree: true});
"""

SEND_PROMPT_JS = """(prompt) => {
    const textarea = document.querySelector('sdc-ai-assistant .ai-prompt-form textarea');
    if (!textarea) return 'The page has no <sdc-ai-assistant> (or SDC_AI_ASSISTANT is off)';
    textarea.value = prompt;
    textarea.closest('form').requestSubmit();
    return null;
}"""

FINAL_STATE_JS = r"""() => {
    const active = (el) => {
        for (let box = el.closest('.sdc_sub_detail_container'); box;
             box = box.parentElement && box.parentElement.closest('.sdc_sub_detail_container')) {
            if (!box.classList.contains('active')) return false;
        }
        return true;
    };
    const own = (el) => !el.closest('sdc-ai-assistant') && active(el);
    let path = [], args = {};
    try {
        const s = window.sdcNav._handleUrl(location.pathname);
        path = s.path || [];
        args = s.args || {};
    } catch (e) { /* no navigator */ }
    const controllers = [...new Set([...document.querySelectorAll('._sdc_controller_')].filter(own).map((el) => {
        const c = window.$ ? $(el).data('_controller_') : null;
        return (c && c._tagName) || el.tagName.toLowerCase();
    }))];
    const fieldValues = (elements) => {
        const values = {}, checks = {};
        for (const el of elements) {
            const type = (el.type || el.tagName).toLowerCase();
            if (!el.name || ['submit', 'button', 'reset', 'image', 'fieldset', 'password', 'hidden', 'file']
                .includes(type)) continue;
            if (type === 'checkbox') {
                (checks[el.name] = checks[el.name] || []).push(el);
            } else if (type === 'radio') {
                if (el.checked) values[el.name] = el.value;
                else if (!(el.name in values)) values[el.name] = null;
            } else if (el.tagName === 'SELECT' && el.multiple) {
                values[el.name] = [...el.selectedOptions].map((o) => o.value);
            } else {
                values[el.name] = el.value;
            }
        }
        for (const [name, boxes] of Object.entries(checks)) {
            values[name] = boxes.length === 1 ? boxes[0].checked : boxes.filter((b) => b.checked).map((b) => b.value);
        }
        return values;
    };
    const forms = [...document.forms].filter(own).map((form) => {
        const pk = form.getAttribute('SdcModelPK');
        return {model: form.getAttribute('SdcModelName'), pk: pk === null ? null : Number(pk),
                values: fieldValues(form.elements)};
    });
    // Fields outside a <form>, grouped by the nearest controller element (as read_page lists them)
    const loose = new Map();
    for (const el of document.body.querySelectorAll('input, select, textarea')) {
        if (el.form || !own(el)) continue;
        let box = el.parentElement;
        while (box && box !== document.body && !box.classList.contains('_sdc_controller_')
               && !box.tagName.includes('-')) box = box.parentElement;
        if (!loose.has(box)) loose.set(box, []);
        loose.get(box).push(el);
    }
    for (const [box, elements] of loose) {
        const c = box && window.$ ? $(box).data('_controller_') : null;
        forms.push({model: null, pk: null, controller: (c && c._tagName) || (box ? box.tagName.toLowerCase() : 'body'),
                    values: fieldValues(elements)});
    }
    return {url: location.pathname, path, args, controllers, forms, submits: window.__sdcEvalSubmits || [],
            error_views: window.__sdcEvalErrorViews || []};
}"""


class Command(BaseCommand):
    help = ('Evaluates the AI assistant: runs task files against a throwaway server for every condition (knowledge '
            'in the system prompt, e.g. none / apps / full) and model, drives the real <sdc-ai-assistant> in a '
            'headless browser and writes one JSON line per episode. --summarize prints the summary of a result file.')

    def add_arguments(self, parser):
        parser.add_argument('tasks', nargs='*', help='Task files or directories (YAML/JSON)')
        parser.add_argument('-o', '--output', default='sdc_eval_results.jsonl',
                            help='Result file (JSON lines). Existing episodes are skipped (resume).')
        parser.add_argument('--condition', action='append', dest='conditions', default=None,
                            help='[label=]source[:skill_file][+extra:file]; source: none, apps, full, auto. '
                                 'Repeatable (default: none, apps, full)')
        parser.add_argument('--model', action='append', dest='models', default=None,
                            help='[label=]provider:model[@base_url], e.g. anthropic:claude-opus-5-5 or '
                                 'openai-compatible:qwen3:32b@https://host/v1. Repeatable (default: the '
                                 'project setting). Keys come from ANTHROPIC_API_KEY / OPENAI_API_KEY.')
        parser.add_argument('--runs', type=int, default=3, help='Repetitions per task, condition and model')
        parser.add_argument('--user', action='append', dest='users', default=[],
                            help='role=username:password (repeatable); users must exist in the fixture')
        parser.add_argument('--users-file', default=None, help='YAML/JSON {role: {username, password}}')
        parser.add_argument('--fixture', action='append', dest='fixtures', default=[],
                            help='Fixture(s) loaded into a flushed database before every episode (repeatable). '
                                 'Without a fixture the database is not reset.')
        parser.add_argument('--database', default='jest',
                            help='DJANGO_DATABASE alias of the evaluation server (default: jest, never your dev DB)')
        parser.add_argument('--effort', default='', help='Effort of the model (SDC_AI_EFFORT)')
        parser.add_argument('--max-tokens', type=int, default=None, help='SDC_AI_MAX_TOKENS')
        parser.add_argument('--only', default=None, help='Regex: only tasks whose id matches')
        parser.add_argument('--seed', type=int, default=1, help='Seed of the random episode order')
        parser.add_argument('--episode-timeout', type=int, default=300, help='Seconds per prompt')
        parser.add_argument('--timeout', type=int, default=15000, help='Timeout of page actions in ms')
        parser.add_argument('--judge-model', default=None,
                            help='Anthropic model that grades tasks with a "judge" rubric (else needs_judge)')
        parser.add_argument('--port', type=int, default=0, help='Port of the evaluation server (default: free)')
        parser.add_argument('--browser-path', default=None, help='Chromium/Chrome executable')
        parser.add_argument('--headed', action='store_true', help='Show the browser window')
        parser.add_argument('--dry-run', action='store_true', help='Validate the tasks and print the plan only')
        parser.add_argument('--summarize', action='store_true',
                            help='Do not run: print the summary of --output (and write --csv)')
        parser.add_argument('--by', default='condition,model', help='Grouping of the summary, e.g. '
                                                                    'condition,model,category')
        parser.add_argument('--csv', default=None, help='Also write one CSV row per episode to this file')

    # ---------------------------------------------------------------------------------------------- handle
    def handle(self, *args, **ops):
        if ops['summarize']:
            return self._summarize(ops)
        try:
            tasks = load_tasks(ops['tasks'] or self._fail('Give task files or directories'))
            if ops['only']:
                import re
                tasks = [t for t in tasks if re.search(ops['only'], t['id'])]
            conditions = [parse_condition(c) for c in ops['conditions'] or ['none', 'apps', 'full']]
            models = [parse_model(m) for m in ops['models'] or [self._project_model()]]
            users = parse_users(ops['users'], ops['users_file'])
        except EvalConfigError as e:
            raise CommandError(str(e))
        self._validate(tasks, conditions, models, users, ops)

        done = {episode_key(r) for r in read_results(ops['output'])}
        rng = random.Random(ops['seed'])
        groups = [(c, m) for c in conditions for m in models]
        rng.shuffle(groups)
        plan = []
        for condition, model in groups:
            episodes = [(t, run) for t in tasks for run in range(ops['runs'])
                        if (t['id'], condition['label'], model['label'], run) not in done]
            rng.shuffle(episodes)
            plan.append((condition, model, episodes))
        total = sum(len(e) for *_, e in plan)
        self.stdout.write(f'{len(tasks)} tasks x {len(conditions)} conditions x {len(models)} models x '
                          f'{ops["runs"]} runs: {total} episodes to run ({len(done)} already in {ops["output"]})')
        if ops['dry_run'] or not total:
            return

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise CommandError('sdc_eval_ai needs playwright: pip install "simpledomcontrol[teach]" && '
                               'playwright install chromium')

        workdir = tempfile.mkdtemp(prefix='sdc_eval_')
        metrics_file = os.path.abspath(ops['output']) + '.metrics.jsonl'
        try:
            with sync_playwright() as p:
                browser = TeachCommand._launch(p, ops, headless=not ops['headed'])
                try:
                    count = 0
                    for condition, model, episodes in plan:
                        if not episodes:
                            continue
                        env = self._group_env(workdir, condition, model, metrics_file, ops)
                        with self._server(env, ops) as base_url:
                            self.stdout.write(self.style.SUCCESS(
                                f'== condition {condition["label"]} / model {model["label"]} ({base_url})'))
                            for task, run in episodes:
                                count += 1
                                result = self._episode(browser, base_url, env, task, run, condition, model,
                                                       users, metrics_file, ops)
                                with open(ops['output'], 'a', encoding='utf-8') as f:
                                    f.write(json.dumps(result, ensure_ascii=False, default=str) + '\n')
                                self.stdout.write(f'[{count}/{total}] {task["id"]} run {run}: {result["outcome"]}'
                                                  + (f' ({result["error"]})' if result.get('error') else ''))
                finally:
                    browser.close()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        self._summarize(ops)

    @staticmethod
    def _fail(msg):
        raise EvalConfigError(msg)

    @staticmethod
    def _project_model():
        provider = getattr(settings, 'SDC_AI_PROVIDER', 'anthropic')
        model = getattr(settings, 'SDC_AI_MODEL', 'claude-opus-5-5')
        base_url = getattr(settings, 'SDC_AI_BASE_URL', '')
        return f'{provider}:{model}' + (f'@{base_url}' if base_url else '')

    def _validate(self, tasks, conditions, models, users, ops):
        if ops['runs'] < 1:
            raise CommandError('--runs must be at least 1')
        for items, kind in ((conditions, 'condition'), (models, 'model')):
            labels = [i['label'] for i in items]
            if len(labels) != len(set(labels)):
                raise CommandError(f'Two {kind}s have the same label {labels}; name them with label=...')
        missing = sorted({t['role'] for t in tasks} - set(users) - {'anonymous'})
        if missing:
            raise CommandError(f'No user for the role(s) {missing}: use --user role=username:password')
        if ops['database'] not in getattr(settings, 'DATABASES_AVAILABLE', {ops['database']: None}):
            raise CommandError(f"DJANGO_DATABASE alias '{ops['database']}' is not defined in your settings")
        base_dir = str(getattr(settings, 'BASE_DIR', ''))
        for c in conditions:
            files = [c['settings']['SDC_AI_SKILL_FILE']] if c['settings']['SDC_AI_SKILL_SOURCE'] == 'full' else []
            files += c['settings']['SDC_AI_ADDITIONAL_SKILL_FILE'] or []
            for file in files:
                if not os.path.isfile(os.path.join(base_dir, file)):
                    raise CommandError(f'Condition {c["label"]}: {file} does not exist (relative to BASE_DIR)')
        keys = {'anthropic': 'ANTHROPIC_API_KEY', 'openai-compatible': 'OPENAI_API_KEY'}
        for m in models:
            key = keys[m['settings']['SDC_AI_PROVIDER']]
            if not os.environ.get(key) and not ops['dry_run']:
                self.stderr.write(self.style.WARNING(f'Model {m["label"]}: {key} is not set'))
        if any('judge' in t['expect'] for t in tasks) and not ops['judge_model']:
            self.stderr.write(self.style.WARNING('Tasks with a judge rubric are marked needs_judge '
                                                 '(no --judge-model)'))

    # ---------------------------------------------------------------------------------------------- server
    def _group_env(self, workdir, condition, model, metrics_file, ops):
        """Environment of the server of one condition/model: a settings module that overrides the AI settings."""
        name = 'sdc_eval_settings_' + hashlib.sha256(f'{condition["spec"]}|{model["spec"]}'.encode()).hexdigest()[:12]
        values = {
            'SDC_AI_ASSISTANT': True, 'SDC_AI_TOKEN_FROM_SYSTEM': True, 'SDC_AI_REQUIRE_LOGIN': True,
            'SDC_AI_ALLOWED_GROUPS': None, 'SDC_AI_MAX_REQUESTS_PER_USER': None, 'SDC_AI_EFFORT': ops['effort'],
            'SDC_AI_METRICS_FILE': metrics_file,
        } | condition['settings'] | model['settings']
        if ops['max_tokens']:
            values['SDC_AI_MAX_TOKENS'] = ops['max_tokens']
        with open(os.path.join(workdir, f'{name}.py'), 'w') as f:
            f.write(settings_module_source(settings.SETTINGS_MODULE, values))
        python_path = os.pathsep.join(filter(None, [workdir, os.getcwd(), os.environ.get('PYTHONPATH')]))
        return os.environ | {'DJANGO_DATABASE': ops['database'], 'DJANGO_SETTINGS_MODULE': name,
                             'PYTHONPATH': python_path}

    def _server(self, env, ops):
        command = self

        class Server:
            def __enter__(self):
                TeachCommand._manage(env, 'migrate', '--noinput')
                port = ops['port'] or TeachCommand._free_port()
                self.base_url = f'http://127.0.0.1:{port}'
                # The server log goes to a file: an unread pipe fills up and blocks the server
                self.log = tempfile.TemporaryFile(mode='w+')
                self.process = subprocess.Popen(
                    [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'],
                    env=env, stdout=self.log, stderr=subprocess.STDOUT, text=True)
                try:
                    TeachCommand._wait_for_server(self.process, self.log, self.base_url)
                except Exception:
                    self.__exit__()
                    raise
                return self.base_url

            def __exit__(self, *exc):
                self.process.terminate()
                try:
                    self.process.wait(10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                if exc and exc[0] is not None:
                    self.log.seek(0)
                    command.stderr.write(self.log.read()[-3000:])
                self.log.close()
                return False

        return Server()

    @staticmethod
    def _state(env, fixtures, users):
        """Resets the database (fixtures not None), creates sessions for ``users``; returns sessions and snapshot."""
        out = TeachCommand._manage(env | {'SDC_EVAL_FIXTURES': json.dumps(fixtures), 'SDC_EVAL_USERS': json.dumps(users)},
                                   'shell', '-c', STATE_SCRIPT)
        line = next((l for l in reversed(out.splitlines()) if l.startswith('SDC_EVAL_STATE ')), None)
        if line is None:
            raise CommandError(f'Unexpected output of the state script:\n{out[-2000:]}')
        return json.loads(line[len('SDC_EVAL_STATE '):])

    # --------------------------------------------------------------------------------------------- episode
    def _episode(self, browser, base_url, env, task, run, condition, model, users, metrics_file, ops):
        prompt = prompt_for_run(task, run)
        result = {
            'task': task['id'], 'app': task['app'], 'category': task['category'], 'role': task['role'],
            'condition': condition['label'], 'condition_spec': condition['spec'], 'model': model['label'],
            'model_spec': model['spec'], 'run': run, 'prompt': prompt, 'followup': task['followup'],
            'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'sdc_version': self._version(),
        }
        started = time.monotonic()
        role_users = {task['role']: users[task['role']]} if task['role'] in users else {}
        episode, error = {}, None
        try:
            before = self._state(env, ops['fixtures'] if ops['fixtures'] else None, role_users)
            session = before['sessions'].get(task['role'])
            if session and 'error' in session:
                raise CommandError(session['error'])
            offset = os.path.getsize(metrics_file) if os.path.exists(metrics_file) else 0
            try:
                episode = self._drive(browser, base_url, session, task, prompt, ops)
            finally:
                after = self._state(env, None, {})
                episode['db_changes'] = db_changes(before['snapshot'], after['snapshot'])
                episode['metric_records'] = self._metric_records(metrics_file, offset)
            error = episode.get('error')
        except Exception as e:  # noqa: BLE001 - one failing episode must not stop the evaluation
            error = f'{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ""}'
        if not error and 'judge' in task['expect'] and ops['judge_model']:
            episode['judge'] = self._judge(ops['judge_model'], [prompt] + task['followup'], task['expect']['judge'],
                                           episode.get('answer', ''))
        checks = check_episode(task, episode) if not error else {}
        result |= {
            'outcome': outcome(checks, error), 'error': error, 'checks': checks,
            'answer': episode.get('answer'), 'answers': episode.get('answers', []),
            'final': episode.get('final'), 'transcript': episode.get('transcript', []),
            'http_errors': episode.get('http_errors', []), 'error_views': episode.get('error_views', []),
            'page_errors': episode.get('page_errors', []),
            'db_changes': episode.get('db_changes', {}), 'submits': episode.get('submits', []),
            'judge': episode.get('judge'),
            'metrics': episode_metrics(episode.get('metric_records', []), episode.get('frames', [])),
            'seconds': round(time.monotonic() - started, 2),
        }
        return result

    def _drive(self, browser, base_url, session, task, prompt, ops):
        """Opens the start page as the task's user, asks the assistant and returns what happened."""
        context = browser.new_context()
        if session:
            context.add_cookies([{'name': session['name'], 'value': session['value'], 'url': base_url}])
        context.add_init_script(SPY_JS)
        frames, http_errors, page_errors, closed = [], [], [], []
        page = context.new_page()
        page.set_default_timeout(ops['timeout'])

        def on_websocket(ws):
            if 'sdc_ws/ai' not in ws.url:
                return

            def record(direction):
                def handler(payload):
                    try:
                        frames.append({'dir': direction, 'data': json.loads(payload)})
                    except (TypeError, ValueError):
                        pass
                return handler
            ws.on('framesent', record('sent'))
            ws.on('framereceived', record('received'))
            ws.on('close', lambda *_: closed.append(True))

        def on_response(response):
            if response.status >= 400 and response.url.startswith(base_url) and 'favicon' not in response.url:
                http_errors.append({'url': response.url[len(base_url):], 'status': response.status})

        page.on('websocket', on_websocket)
        page.on('response', on_response)
        page.on('pageerror', lambda exc: page_errors.append(str(exc)))
        page.on('dialog', lambda dialog: dialog.dismiss())
        episode = {'frames': frames, 'http_errors': http_errors, 'page_errors': page_errors, 'answers': []}
        try:
            page.goto(base_url + task['start'], wait_until='domcontentloaded')
            self._wait_ready(page, ops)
            if not self._wait_for(page, lambda: any(f['dir'] == 'received' and f['data'].get('type') in
                                                    ('ai_config', 'error') for f in frames), 20):
                raise CommandError('The assistant did not connect (is <sdc-ai-assistant> in the base template?)')
            connect_error = next((f['data'] for f in frames if f['data'].get('type') == 'error'), None)
            if connect_error:
                raise CommandError(f'Assistant: {connect_error.get("msg")}')
            # Errors of the start page are not the assistant's
            http_errors.clear()
            page.evaluate('() => { window.__sdcEvalErrorViews = []; }')
            for text in [prompt] + task['followup']:
                answer = self._ask(page, frames, closed, text, ops)
                episode['answers'].append(answer)
            episode['answer'] = episode['answers'][-1]
            self._wait_ready(page, ops)
            final = page.evaluate(FINAL_STATE_JS)
            episode['submits'] = final.pop('submits')
            episode['error_views'] = final.pop('error_views')
            episode['final'] = final
        except Exception as e:  # noqa: BLE001
            episode['error'] = f'{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ""}'
        finally:
            context.close()
        episode['tool_results'], episode['transcript'] = self._transcript(frames)
        return episode

    def _ask(self, page, frames, closed, text, ops):
        start = len(frames)
        problem = page.evaluate(SEND_PROMPT_JS, text)
        if problem:
            raise CommandError(problem)

        def end():
            return next((f['data'] for f in frames[start:] if f['dir'] == 'received' and f['data'].get('id') is not None
                         and f['data'].get('type') in ('ai_answer', 'error')), None)
        if not self._wait_for(page, lambda: end() is not None or closed, ops['episode_timeout']):
            raise CommandError(f'No answer within {ops["episode_timeout"]}s')
        data = end()
        if data is None:
            raise CommandError('The assistant disconnected')
        if data['type'] == 'error':
            raise CommandError(f'Assistant error: {data.get("msg")}')
        return data.get('text', '')

    @staticmethod
    def _wait_for(page, condition, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return True
            page.wait_for_timeout(200)
        return condition()

    @staticmethod
    def _wait_ready(page, ops):
        try:
            page.wait_for_function(WAIT_READY_JS, timeout=ops['timeout'])
        except Exception:  # noqa: BLE001 - a slow page is judged by the checks
            pass

    @staticmethod
    def _transcript(frames):
        """All tool results as text (for the forbidden check) and a compact transcript of the actions."""
        names = {}
        texts, transcript = [], []
        for f in frames:
            data = f['data']
            if f['dir'] == 'received' and data.get('type') == 'ai_actions':
                for action in data.get('actions') or []:
                    names[action.get('tool_use_id')] = action.get('name')
                    transcript.append({'action': action.get('name'), 'input': action.get('input'),
                                       'tool_use_id': action.get('tool_use_id')})
            elif f['dir'] == 'sent' and data.get('event') == 'action_results':
                for r in data.get('results') or []:
                    content = r.get('content')
                    content = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                    texts.append(content)
                    transcript.append({'result': names.get(r.get('tool_use_id')), 'is_error': bool(r.get('is_error')),
                                       'tool_use_id': r.get('tool_use_id'), 'content': content[:500]})
        return texts, transcript

    @staticmethod
    def _metric_records(path, offset):
        if not os.path.exists(path):
            return []
        with open(path, encoding='utf-8') as f:
            f.seek(offset)
            return [json.loads(line) for line in f if line.strip()]

    @staticmethod
    def _judge(model, prompts, rubric, answer):
        try:
            import anthropic
        except ImportError:
            raise CommandError('--judge-model needs the anthropic package: pip install "simpledomcontrol[ai]"')
        message = anthropic.Anthropic().messages.create(
            model=model, max_tokens=300,
            messages=[{'role': 'user', 'content': JUDGE_PROMPT.format(
                prompt='\n'.join(prompts), rubric=rubric, answer=answer or '(no answer)')}])
        text = ''.join(b.text for b in message.content if b.type == 'text')
        return parse_judge(text) | {'model': model}

    @staticmethod
    def _version():
        try:
            return version('SimpleDomControl')
        except PackageNotFoundError:
            return None

    # --------------------------------------------------------------------------------------------- summary
    def _summarize(self, ops):
        results = read_results(ops['output'])
        if not results:
            raise CommandError(f'No results in {ops["output"]}')
        by = tuple(k.strip() for k in ops['by'].split(',') if k.strip())
        self.stdout.write(format_table(summarize(results, by)))
        for warning in prompt_warnings(results):
            self.stderr.write(self.style.WARNING(warning))
        if ops['csv']:
            write_csv(results, ops['csv'])
            self.stdout.write(self.style.SUCCESS(f'Wrote {ops["csv"]}'))
