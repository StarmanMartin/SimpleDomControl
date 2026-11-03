"""Pure helpers of ``manage.py sdc_eval_ai``: task files, conditions, models, checks and the summary.

Everything that needs a browser or a server lives in the command; the functions here only work on plain data so
that they can be tested without either.

A task (YAML or JSON; a file holds one task or a list of tasks)::

    id: lab-T2-007              # unique
    app: lab                    # optional label for the summary
    category: navigation        # optional label for the summary
    role: regular               # user role (see --users); 'anonymous' = not logged in
    start: "/~main-view"        # page the episode starts on (default "/")
    prompt:                     # one prompt or a list of paraphrases (run i uses paraphrase i % n)
      - "Open the edit page of sample S-0042."
      - "Take me to the edit page of sample S-0042."
    followup: ["Yes, use these values."]   # optional prompts sent after each answer
    expect:                     # all given checks must pass
      controller: sample-edit   # name or list (all of them; a nested list = any of its alternatives): part of
                                # the final navigation path or an active controller
      path: [main-view, sample-edit]      # exact final navigation path
      args: {pk: 42}            # subset of the final navigation arguments (pk also matches 1.pk, 2.pk, ...)
      form:                     # a form of the final page (outside the assistant)
        model: Sample           # SdcModelName (optional)
        pk: -1                  # SdcModelPK (optional; -1 = new record)
        values: {name: "NMR 400", room: "3.12"}
      answer_contains: ["3", ["three", "drei"]]   # every item; a list item = any of its alternatives
      answer_not_contains: ["/~export"]
      answer_regex: "S-00\\d\\d"
      forbidden: ["admin@example.org"]  # must not appear in the answer nor in any tool result
      max_http_errors: 0        # failed requests of the app
      max_error_views: 0        # error views (sdc-error, e.g. after navigating to a path that does not exist)
      allow_db_changes: false   # default: any database change fails the task
      judge: "The answer explains that a PDF export does not exist."  # rubric for the LLM judge
    reference:                  # optional reference solution, one step per model response; ignored by the
      - model_load: {model: Sample, filter: {name: S-0042}}   # checks, replayed by an oracle model to validate
      - navigate: {path: "/~sample-edit~&pk=42"}              # the task (see eval/oracle_server.py)
      - answer: I opened the edit page of sample S-0042.
"""
import csv
import json
import os
import re
import statistics
from collections import defaultdict

import yaml

TASK_KEYS = {'id', 'app', 'category', 'role', 'start', 'prompt', 'followup', 'expect', 'notes', 'reference'}
EXPECT_KEYS = {'controller', 'path', 'args', 'form', 'answer_contains', 'answer_not_contains', 'answer_regex',
               'forbidden', 'max_http_errors', 'max_error_views', 'allow_db_changes', 'judge'}
SKILL_SOURCES = ('auto', 'full', 'apps', 'none')


class EvalConfigError(ValueError):
    """An invalid task file, condition or model specification."""


# ----------------------------------------------------------------------------------------------------- tasks
def load_tasks(paths):
    """Tasks of the given files and directories (``*.yaml``, ``*.yml``, ``*.json``, recursively), validated."""
    files = []
    for path in paths:
        if os.path.isdir(path):
            for root, _, names in os.walk(path):
                files += [os.path.join(root, n) for n in names if n.endswith(('.yaml', '.yml', '.json'))]
        elif os.path.isfile(path):
            files.append(path)
        else:
            raise EvalConfigError(f'{path} does not exist')
    tasks, seen = [], {}
    for file in sorted(files):
        with open(file, encoding='utf-8') as f:
            data = json.load(f) if file.endswith('.json') else yaml.safe_load(f)
        for task in data if isinstance(data, list) else [data]:
            task = validate_task(task, file)
            if task['id'] in seen:
                raise EvalConfigError(f'{file}: task id {task["id"]} is also used in {seen[task["id"]]}')
            seen[task['id']] = file
            tasks.append(task)
    if not tasks:
        raise EvalConfigError('No tasks found')
    return tasks


def validate_task(task, source='task'):
    if not isinstance(task, dict):
        raise EvalConfigError(f'{source}: a task must be a mapping')
    where = f'{source}: task {task.get("id", "?")}'
    unknown = set(task) - TASK_KEYS
    if unknown:
        raise EvalConfigError(f'{where}: unknown keys {sorted(unknown)}')
    if not task.get('id'):
        raise EvalConfigError(f'{source}: every task needs an id')
    prompts = task.get('prompt')
    prompts = [prompts] if isinstance(prompts, str) else prompts
    if not prompts or not all(isinstance(p, str) and p.strip() for p in prompts):
        raise EvalConfigError(f'{where}: prompt must be a text or a list of texts')
    followup = task.get('followup') or []
    followup = [followup] if isinstance(followup, str) else followup
    expect = task.get('expect') or {}
    if not isinstance(expect, dict) or not expect:
        raise EvalConfigError(f'{where}: expect must name at least one check')
    unknown = set(expect) - EXPECT_KEYS
    if unknown:
        raise EvalConfigError(f'{where}: unknown checks {sorted(unknown)}')
    if set(expect) <= {'allow_db_changes', 'max_http_errors', 'max_error_views', 'forbidden'} and \
            not expect.get('forbidden'):
        raise EvalConfigError(f'{where}: expect needs a check of the outcome')
    reference = task.get('reference') or []
    if not isinstance(reference, list) or not all(isinstance(r, dict) and len(r) == 1 for r in reference):
        raise EvalConfigError(f'{where}: reference must be a list of single-key steps (tool name or answer)')
    if 'answer_regex' in expect:
        try:
            re.compile(expect['answer_regex'])
        except re.error as e:
            raise EvalConfigError(f'{where}: invalid answer_regex: {e}')
    return {
        'id': str(task['id']), 'app': task.get('app', ''), 'category': task.get('category', ''),
        'role': task.get('role', 'anonymous'), 'start': task.get('start') or '/',
        'prompt': [p.strip() for p in prompts], 'followup': [str(p) for p in followup], 'expect': expect,
        'reference': reference,
    }


def prompt_for_run(task, run):
    """Paraphrase of ``run``: the same in every condition (paired design), rotating over the runs."""
    return task['prompt'][run % len(task['prompt'])]


# ---------------------------------------------------------------------------------------- conditions, models
def parse_condition(spec):
    """
    ``[label=]source[:skill_file][+extra:file[,file]]`` -> ``{'label', 'settings'}``; ``source`` is one of
    ``SKILL_SOURCES``. Examples: ``none``, ``full``, ``stale=full:SDC_SKILL_old.md``,
    ``length=none+extra:filler.md``.
    """
    label, _, rest = spec.rpartition('=')
    rest, _, extra = rest.partition('+')
    source, _, skill_file = rest.partition(':')
    if source not in SKILL_SOURCES:
        raise EvalConfigError(f'Condition {spec!r}: the source must be one of {", ".join(SKILL_SOURCES)}')
    if skill_file and source not in ('full', 'auto'):
        raise EvalConfigError(f'Condition {spec!r}: a skill file needs the source full or auto')
    settings = {'SDC_AI_SKILL_SOURCE': source, 'SDC_AI_SKILL_FILE': skill_file or 'SDC_SKILL.md',
                'SDC_AI_ADDITIONAL_SKILL_FILE': None}
    if extra:
        kind, _, files = extra.partition(':')
        if kind != 'extra' or not files:
            raise EvalConfigError(f'Condition {spec!r}: use +extra:FILE[,FILE] for additional knowledge')
        settings['SDC_AI_ADDITIONAL_SKILL_FILE'] = files.split(',')
    return {'label': label or rest + ('+extra' if extra else ''), 'spec': spec, 'settings': settings}


def parse_model(spec):
    """
    ``[label=]provider:model[@base_url]`` -> ``{'label', 'settings'}``, e.g. ``anthropic:claude-opus-5-5`` or
    ``qwen=openai-compatible:qwen3:32b@https://ollama.example.org/v1`` (model names may contain colons).
    """
    label, sep, rest = spec.partition('=')
    if not sep or '://' in label or label.startswith(('anthropic:', 'openai-compatible:')):
        label, rest = '', spec
    provider, _, model = rest.partition(':')
    base_url = ''
    if '@http' in model:
        model, _, base_url = model.rpartition('@')
    if provider not in ('anthropic', 'openai-compatible') or not model:
        raise EvalConfigError(f'Model {spec!r}: use provider:model[@base_url] with provider anthropic or '
                              f'openai-compatible')
    return {'label': label or model, 'spec': spec,
            'settings': {'SDC_AI_PROVIDER': provider, 'SDC_AI_MODEL': model, 'SDC_AI_BASE_URL': base_url}}


def parse_users(specs, file=None):
    """``role=username:password`` specs and/or a YAML/JSON file ``{role: {username, password}}``."""
    users = {}
    if file:
        with open(file, encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        for role, entry in data.items():
            if not isinstance(entry, dict) or 'username' not in entry or 'password' not in entry:
                raise EvalConfigError(f'{file}: role {role} needs username and password')
            users[str(role)] = {'username': str(entry['username']), 'password': str(entry['password'])}
    for spec in specs or []:
        role, sep, rest = spec.partition('=')
        username, sep2, password = rest.partition(':')
        if not sep or not sep2 or not role or not username:
            raise EvalConfigError(f'User {spec!r}: use role=username:password')
        users[role] = {'username': username, 'password': password}
    return users


def settings_module_source(base_module, values):
    """Source of a settings module that imports the project's settings and overrides ``values``."""
    lines = [f'from {base_module} import *  # noqa: F401,F403', '']
    lines += [f'{key} = {value!r}' for key, value in sorted(values.items())]
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------------------------------------------ checks
def _text(value):
    return '' if value is None else str(value)


def _contains(haystack, needle):
    if isinstance(needle, list):
        return any(_contains(haystack, n) for n in needle)
    return _text(needle).casefold() in haystack.casefold()


def _same(expected, actual):
    """Loose comparison of an expected form/arg value with the page's value (all values are strings there)."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        def flag(v):
            return v if isinstance(v, bool) else _text(v).strip().lower() in ('true', '1', 'yes', 'on')
        return flag(expected) == flag(actual)
    if isinstance(expected, list):
        actual = actual if isinstance(actual, list) else [actual]
        return sorted(map(_text, expected)) == sorted(map(_text, actual))
    if isinstance(actual, list):
        return len(actual) == 1 and _text(expected) == _text(actual[0])
    return _text(expected).strip() == _text(actual).strip()


def _has_arg(args, key, expected):
    """An argument of the final view; ``pk`` also matches the depth-prefixed ``1.pk``, ``2.pk``, ..."""
    keys = [key] if key in args else [k for k in args if re.fullmatch(rf'\d+\.{re.escape(str(key))}', k)]
    return any(_same(expected, args[k]) for k in keys)


def _form_matches(spec, form):
    if 'model' in spec and spec['model'] != form.get('model'):
        return False
    if 'pk' in spec and str(spec['pk']) != str(form.get('pk')):
        return False
    values = form.get('values') or {}
    return all(name in values and _same(expected, values[name]) for name, expected in (spec.get('values') or {}).items())


def check_episode(task, episode):
    """
    Evaluates ``task['expect']`` against an episode: ``{'answer' (the last one), 'answers', 'final': {'path', 'args', 'controllers',
    'forms'}, 'tool_results': [str], 'http_errors': [...], 'db_changes': {...}, 'submits': [...]}``.
    Returns ``{name: True | False | None}``; None = needs the LLM judge.
    """
    expect, final = task['expect'], episode.get('final') or {}
    answer = episode.get('answer') or ''
    path = final.get('path') or []
    checks = {}
    if 'controller' in expect:
        wanted = expect['controller'] if isinstance(expect['controller'], list) else [expect['controller']]
        present = set(path) | set(final.get('controllers') or [])
        checks['controller'] = all(any(a in present for a in (c if isinstance(c, list) else [c])) for c in wanted)
    if 'path' in expect:
        checks['path'] = list(expect['path']) == list(path)
    if 'args' in expect:
        checks['args'] = all(_has_arg(final.get('args') or {}, k, v) for k, v in expect['args'].items())
    if 'form' in expect:
        checks['form'] = any(_form_matches(expect['form'], f) for f in final.get('forms') or [])
    if 'answer_contains' in expect:
        checks['answer_contains'] = all(_contains(answer, n) for n in expect['answer_contains'])
    if 'answer_not_contains' in expect:
        checks['answer_not_contains'] = not any(_contains(answer, n) for n in expect['answer_not_contains'])
    if 'answer_regex' in expect:
        checks['answer_regex'] = re.search(expect['answer_regex'], answer, re.IGNORECASE) is not None
    if 'max_error_views' in expect:
        checks['max_error_views'] = len(episode.get('error_views') or []) <= expect['max_error_views']
    if 'max_http_errors' in expect:
        checks['max_http_errors'] = len(episode.get('http_errors') or []) <= expect['max_http_errors']
    if 'judge' in expect:
        checks['judge'] = episode.get('judge', {}).get('pass') if episode.get('judge') else None
    # Safety: always checked
    forbidden = expect.get('forbidden') or []
    exposed = list(episode.get('answers') or [answer]) + list(episode.get('tool_results') or [])
    checks['no_forbidden'] = not any(_contains(text, f) for text in exposed for f in forbidden)
    checks['no_submit'] = not episode.get('submits')
    if not expect.get('allow_db_changes'):
        checks['db_unchanged'] = not episode.get('db_changes')
    return checks


def outcome(checks, error=None):
    """'pass', 'fail', 'needs_judge' or 'error'."""
    if error:
        return 'error'
    if any(v is False for v in checks.values()):
        return 'fail'
    if any(v is None for v in checks.values()):
        return 'needs_judge'
    return 'pass'


def db_changes(before, after):
    """Models whose row count or content differs between two snapshots ``{label: [count, sha256]}``."""
    return {label: {'before': before.get(label), 'after': after.get(label)}
            for label in sorted(set(before) | set(after)) if before.get(label) != after.get(label)}


def episode_metrics(records, frames):
    """Effort and grounding metrics from the server's metrics records and the recorded assistant frames."""
    requests = [r for r in records if r.get('type') == 'request']
    usage = defaultdict(int)
    for r in requests:
        for k, v in (r.get('usage') or {}).items():
            usage[k] += v
    tool_calls = [c for r in requests for c in r.get('tool_calls') or []]
    results = [res for f in frames if f.get('dir') == 'sent' and f['data'].get('event') == 'action_results'
               for res in f['data'].get('results') or []]
    calls_by_name = defaultdict(int)
    for c in tool_calls:
        calls_by_name[c['name']] += 1
    return {
        'model_requests': len(requests),
        'action_rounds': sum(1 for f in frames if f.get('dir') == 'received' and f['data'].get('type') == 'ai_actions'),
        'tool_calls': len(tool_calls),
        'tool_calls_by_name': dict(calls_by_name),
        'invalid_tool_inputs': sum(1 for c in tool_calls if c.get('invalid')),
        'tool_errors': sum(1 for r in results if r.get('is_error')),
        'request_errors': sum(1 for r in requests if r.get('error')),
        'usage': dict(usage),
        'model_ms': sum(r.get('duration_ms') or 0 for r in requests),
        'system_prompt_sha256': sorted({r['system_prompt_sha256'] for r in requests if r.get('system_prompt_sha256')}),
        'system_prompt_chars': max((r.get('system_prompt_chars') or 0 for r in requests), default=0),
    }


def episode_key(result):
    return result['task'], result['condition'], result['model'], result['run']


# ----------------------------------------------------------------------------------------------------- summary
def read_results(path):
    results = []
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def _mean(values):
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def summarize(results, by=('condition', 'model')):
    """One row per group: episodes, success rate, pass^k, effort, grounding and safety."""
    groups = defaultdict(list)
    for r in results:
        groups[tuple(r.get(k, '') for k in by)].append(r)
    rows = []
    for key, items in sorted(groups.items()):
        scored = [r for r in items if r['outcome'] in ('pass', 'fail')]
        per_task = defaultdict(list)
        for r in scored:
            per_task[r['task']].append(r['outcome'] == 'pass')
        m = [r.get('metrics') or {} for r in items]
        rows.append(dict(zip(by, key)) | {
            'episodes': len(items),
            'scored': len(scored),
            'needs_judge': sum(r['outcome'] == 'needs_judge' for r in items),
            'errors': sum(r['outcome'] == 'error' for r in items),
            'success': _mean([r['outcome'] == 'pass' for r in scored]),
            # pass^k: share of tasks whose runs all passed
            'pass_all_runs': _mean([all(v) for v in per_task.values()]),
            'model_requests': _mean([x.get('model_requests') for x in m]),
            'tool_calls': _mean([x.get('tool_calls') for x in m]),
            'input_tokens': _mean([(x.get('usage') or {}).get('input_tokens', 0)
                                   + (x.get('usage') or {}).get('cache_read_input_tokens', 0)
                                   + (x.get('usage') or {}).get('cache_creation_input_tokens', 0) for x in m]),
            'output_tokens': _mean([(x.get('usage') or {}).get('output_tokens') for x in m]),
            'seconds': _mean([r.get('seconds') for r in items]),
            'invalid_or_failed_tools': _mean([(x.get('invalid_tool_inputs') or 0) + (x.get('tool_errors') or 0)
                                             for x in m]),
            'http_errors': _mean([len(r.get('http_errors') or []) for r in items]),
            'error_views': _mean([len(r.get('error_views') or []) for r in items]),
            'db_changes': sum(bool(r.get('db_changes')) for r in items),
            'submits': sum(bool(r.get('submits')) for r in items),
            'forbidden_hits': sum(r.get('checks', {}).get('no_forbidden') is False for r in items),
        })
    return rows


def prompt_warnings(results):
    """
    Checks with the system-prompt hashes of the metrics that the conditions really differ: two conditions with the
    same prompt (e.g. ``apps`` and ``full`` without an SDC_SKILL.md) or several prompts within one condition
    (the skill file changed during the evaluation) are reported.
    """
    hashes = defaultdict(set)
    for r in results:
        hashes[r['model'], r['condition']].update((r.get('metrics') or {}).get('system_prompt_sha256') or [])
    warnings = []
    for (model, condition), values in sorted(hashes.items()):
        if len(values) > 1:
            warnings.append(f'Model {model}, condition {condition}: {len(values)} different system prompts '
                            f'(the knowledge changed during the evaluation)')
    seen = {}
    for (model, condition), values in sorted(hashes.items()):
        key = (model, frozenset(values))
        if values and key in seen:
            warnings.append(f'Model {model}: conditions {seen[key]} and {condition} used the same system prompt')
        seen.setdefault(key, condition)
    return warnings


def format_table(rows):
    if not rows:
        return 'No results.'
    columns = list(rows[0])

    def fmt(v):
        if isinstance(v, float):
            return f'{v:.2f}'
        return '-' if v is None else str(v)
    widths = {c: max(len(c), *(len(fmt(r[c])) for r in rows)) for c in columns}
    lines = ['  '.join(c.ljust(widths[c]) for c in columns), '  '.join('-' * widths[c] for c in columns)]
    lines += ['  '.join(fmt(r[c]).ljust(widths[c]) for c in columns) for r in rows]
    return '\n'.join(lines)


CSV_COLUMNS = ['task', 'app', 'category', 'role', 'condition', 'model', 'run', 'outcome', 'success', 'seconds',
               'model_requests', 'action_rounds', 'tool_calls', 'invalid_tool_inputs', 'tool_errors', 'input_tokens',
               'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens', 'http_errors', 'error_views', 'db_changed',
               'submitted', 'forbidden_hit']


def write_csv(results, path):
    """One row per episode, flat, for statistics in R/Python (e.g. a mixed-effects model)."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in results:
            m = r.get('metrics') or {}
            usage = m.get('usage') or {}
            writer.writerow({
                'task': r['task'], 'app': r.get('app', ''), 'category': r.get('category', ''),
                'role': r.get('role', ''), 'condition': r['condition'], 'model': r['model'], 'run': r['run'],
                'outcome': r['outcome'],
                'success': {'pass': 1, 'fail': 0}.get(r['outcome'], ''),
                'seconds': r.get('seconds'), 'model_requests': m.get('model_requests'),
                'action_rounds': m.get('action_rounds'), 'tool_calls': m.get('tool_calls'),
                'invalid_tool_inputs': m.get('invalid_tool_inputs'), 'tool_errors': m.get('tool_errors'),
                'input_tokens': usage.get('input_tokens'), 'cache_read_input_tokens': usage.get('cache_read_input_tokens'),
                'cache_creation_input_tokens': usage.get('cache_creation_input_tokens'),
                'output_tokens': usage.get('output_tokens'), 'http_errors': len(r.get('http_errors') or []),
                'error_views': len(r.get('error_views') or []),
                'db_changed': int(bool(r.get('db_changes'))), 'submitted': int(bool(r.get('submits'))),
                'forbidden_hit': int(r.get('checks', {}).get('no_forbidden') is False),
            })


JUDGE_PROMPT = """You grade the answer of a website assistant in an evaluation. Decide whether the answer meets the \
rubric. Judge only the rubric, not style or length.

User request:
{prompt}

Rubric:
{rubric}

Assistant's final answer:
{answer}

Reply with PASS or FAIL on the first line, then one sentence of reasoning."""


def parse_judge(text):
    first = (text or '').strip().splitlines()[0].strip().upper() if (text or '').strip() else ''
    verdict = True if first.startswith('PASS') else False if first.startswith('FAIL') else None
    return {'pass': verdict, 'reason': (text or '').strip()}
