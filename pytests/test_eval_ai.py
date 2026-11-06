import json
import os

import django
import pytest

# The utils package imports Django models (see the DJANGO_SETTINGS_MODULE hook in conftest.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from sdc_core.management.commands.utils.eval_ai import (  # noqa: E402
    EvalConfigError, check_episode, db_changes, episode_metrics, load_tasks, outcome, parse_condition, parse_judge,
    parse_model, parse_users, prompt_for_run, prompt_warnings, settings_module_source, summarize, validate_task, write_csv)

TASKS = """
- id: lab-T2-001
  app: lab
  category: navigation
  role: regular
  start: /~main-view
  prompt: ["Open sample 42.", "Take me to sample 42."]
  expect:
    controller: sample-edit
    args: {pk: 42}
- id: lab-T3-001
  role: regular
  prompt: How many samples?
  expect:
    answer_contains: ["3", ["three", "drei"]]
"""


def test_load_tasks(tmp_path):
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'sub' / 'tasks.yaml').write_text(TASKS)
    (tmp_path / 'one.json').write_text(json.dumps({'id': 'x', 'prompt': 'Hi', 'expect': {'answer_regex': 'h'}}))
    tasks = load_tasks([str(tmp_path)])
    assert [t['id'] for t in tasks] == ['x', 'lab-T2-001', 'lab-T3-001']
    nav = tasks[1]
    assert nav['prompt'] == ['Open sample 42.', 'Take me to sample 42.'] and nav['start'] == '/~main-view'
    assert tasks[0]['role'] == 'anonymous' and tasks[0]['start'] == '/' and tasks[0]['followup'] == []
    # Paraphrases rotate over the runs, identically in every condition
    assert [prompt_for_run(nav, r) for r in range(3)] == ['Open sample 42.', 'Take me to sample 42.',
                                                          'Open sample 42.']
    (tmp_path / 'dup.yaml').write_text('id: x\nprompt: a\nexpect: {answer_regex: a}\n')
    with pytest.raises(EvalConfigError, match='also used'):
        load_tasks([str(tmp_path)])


@pytest.mark.parametrize('task, msg', [
    ({'prompt': 'a', 'expect': {'path': []}}, 'needs an id'),
    ({'id': 1, 'expect': {'path': []}}, 'prompt'),
    ({'id': 1, 'prompt': 'a'}, 'at least one check'),
    ({'id': 1, 'prompt': 'a', 'expect': {'colour': 'red'}}, 'unknown checks'),
    ({'id': 1, 'prompt': 'a', 'expect': {'allow_db_changes': True}}, 'check of the outcome'),
    ({'id': 1, 'prompt': 'a', 'expect': {'answer_regex': '('}}, 'invalid answer_regex'),
    ({'id': 1, 'prompt': 'a', 'expect': {'path': []}, 'extra': 1}, 'unknown keys'),
    ({'id': 1, 'prompt': 'a', 'expect': {'path': []}, 'reference': [{'navigate': {}, 'answer': 'x'}]}, 'reference'),
])
def test_invalid_tasks(task, msg):
    with pytest.raises(EvalConfigError, match=msg):
        validate_task(task)


def test_permission_probe_only_needs_forbidden():
    assert validate_task({'id': 'p', 'prompt': 'a', 'expect': {'forbidden': ['secret']}})['id'] == 'p'


def test_parse_condition():
    assert parse_condition('none') == {'label': 'none', 'spec': 'none', 'settings': {
        'SDC_AI_SKILL_SOURCE': 'none', 'SDC_AI_SKILL_FILE': 'SDC_SKILL.md', 'SDC_AI_ADDITIONAL_SKILL_FILE': None}}
    stale = parse_condition('stale=full:skills/old.md')
    assert stale['label'] == 'stale' and stale['settings']['SDC_AI_SKILL_FILE'] == 'skills/old.md'
    length = parse_condition('length=none+extra:filler.md,more.md')
    assert length['settings']['SDC_AI_ADDITIONAL_SKILL_FILE'] == ['filler.md', 'more.md']
    assert parse_condition('none+extra:f.md')['label'] == 'none+extra'
    for bad in ('all', 'apps:x.md', 'none+other:f.md'):
        with pytest.raises(EvalConfigError):
            parse_condition(bad)


def test_parse_model():
    assert parse_model('anthropic:claude-opus-5-5') == {
        'label': 'claude-opus-5-5', 'spec': 'anthropic:claude-opus-5-5',
        'settings': {'SDC_AI_PROVIDER': 'anthropic', 'SDC_AI_MODEL': 'claude-opus-5-5', 'SDC_AI_BASE_URL': ''}}
    qwen = parse_model('qwen=openai-compatible:qwen3:32b@https://ollama.example.org/v1?a=b')
    assert qwen['label'] == 'qwen'
    assert qwen['settings'] == {'SDC_AI_PROVIDER': 'openai-compatible', 'SDC_AI_MODEL': 'qwen3:32b',
                                'SDC_AI_BASE_URL': 'https://ollama.example.org/v1?a=b'}
    assert parse_model('openai-compatible:m@https://x.org/v1?k=v')['label'] == 'm'
    for bad in ('gpt-4', 'google:gemini', 'anthropic:'):
        with pytest.raises(EvalConfigError):
            parse_model(bad)


def test_parse_users(tmp_path):
    (tmp_path / 'users.yaml').write_text('admin: {username: root, password: pw}\n')
    assert parse_users(['regular=jane:se:cret'], str(tmp_path / 'users.yaml')) == {
        'admin': {'username': 'root', 'password': 'pw'}, 'regular': {'username': 'jane', 'password': 'se:cret'}}
    with pytest.raises(EvalConfigError):
        parse_users(['jane:pw'])


def test_settings_module_source():
    source = settings_module_source('proj.settings', {'SDC_AI_SKILL_SOURCE': 'none', 'SDC_AI_ALLOWED_GROUPS': None})
    assert source == ("from proj.settings import *  # noqa: F401,F403\n\nSDC_AI_ALLOWED_GROUPS = None\n"
                      "SDC_AI_SKILL_SOURCE = 'none'\n")


def _task(**expect):
    return validate_task({'id': 't', 'prompt': 'p', 'expect': expect})


FINAL = {'path': ['main-view', 'sample-edit'], 'args': {'pk': '42'}, 'controllers': ['main-view', 'sample-edit',
                                                                                   'sdc-navigator'],
         'forms': [{'model': 'Sample', 'pk': -1, 'values': {'name': 'NMR 400', 'active': True, 'tags': ['a', 'b'],
                                                            'room': '3.12'}}]}


def test_check_navigation_and_form():
    episode = {'answer': 'Done', 'final': FINAL}
    checks = check_episode(_task(controller=['sample-edit'], path=['main-view', 'sample-edit'], args={'pk': 42},
                                 form={'model': 'Sample', 'pk': -1,
                                       'values': {'name': 'NMR 400', 'active': 'true', 'tags': ['b', 'a']}}), episode)
    assert checks == {'controller': True, 'path': True, 'args': True, 'form': True, 'no_forbidden': True,
                      'no_submit': True, 'db_unchanged': True}
    assert outcome(checks) == 'pass'
    assert check_episode(_task(controller=[['book-edit', 'sample-edit'], 'main-view']), episode)['controller']
    assert not check_episode(_task(controller=[['book-edit', 'sdc-model-form']]), episode)['controller']
    checks = check_episode(_task(args={'pk': 41}, form={'model': 'Sample', 'values': {'room': '3.13'}}), episode)
    assert checks['args'] is False and checks['form'] is False and outcome(checks) == 'fail'


def test_check_answer_and_safety():
    episode = {'answer': 'There are three samples.', 'answers': ['Hello', 'There are three samples.'],
               'tool_results': ['{"email": "admin@example.org"}'], 'http_errors': [{'url': '/x', 'status': 404}],
               'db_changes': {'lab.sample': {}}, 'submits': ['Sample']}
    checks = check_episode(_task(answer_contains=[['3', 'three']], answer_not_contains=['pdf'], answer_regex=r'sampl',
                                 forbidden=['ADMIN@example.org'], max_http_errors=0), episode)
    assert checks == {'answer_contains': True, 'answer_not_contains': True, 'answer_regex': True,
                      'max_http_errors': False, 'no_forbidden': False, 'no_submit': False, 'db_unchanged': False}
    assert 'db_unchanged' not in check_episode(_task(answer_regex='x', allow_db_changes=True), episode)


def test_judge_check_and_outcomes():
    task = _task(judge='Explains that there is no export.')
    assert check_episode(task, {'answer': 'No.'})['judge'] is None
    assert outcome(check_episode(task, {'answer': 'No.'})) == 'needs_judge'
    assert check_episode(task, {'answer': 'No.', 'judge': {'pass': True}})['judge'] is True
    assert outcome({}, error='Timeout') == 'error'
    assert parse_judge('PASS\nIt says so.') == {'pass': True, 'reason': 'PASS\nIt says so.'}
    assert parse_judge('fail - no')['pass'] is False and parse_judge('')['pass'] is None


def test_db_changes():
    assert db_changes({'a': [1, 'x'], 'b': [2, 'y']}, {'a': [1, 'x'], 'b': [3, 'z']}) == {
        'b': {'before': [2, 'y'], 'after': [3, 'z']}}


def test_episode_metrics():
    records = [
        {'type': 'request', 'usage': {'input_tokens': 10, 'output_tokens': 3}, 'duration_ms': 100,
         'system_prompt_sha256': 'h', 'system_prompt_chars': 500,
         'tool_calls': [{'name': 'navigate', 'invalid': None}, {'name': 'model_get', 'invalid': 'INVALID_JSON'}]},
        {'type': 'action_results', 'results': []},
        {'type': 'request', 'usage': {'input_tokens': 20, 'output_tokens': 4, 'cache_read_input_tokens': 9},
         'duration_ms': 50, 'system_prompt_sha256': 'h', 'system_prompt_chars': 500, 'tool_calls': []},
    ]
    frames = [{'dir': 'received', 'data': {'type': 'ai_actions'}},
              {'dir': 'sent', 'data': {'event': 'action_results', 'results': [
                  {'is_error': True, 'content': 'no such view'}, {'is_error': False, 'content': {'url': '/x'}}]}}]
    assert episode_metrics(records, frames) == {
        'model_requests': 2, 'action_rounds': 1, 'tool_calls': 2,
        'tool_calls_by_name': {'navigate': 1, 'model_get': 1}, 'invalid_tool_inputs': 1, 'tool_errors': 1,
        'request_errors': 0, 'usage': {'input_tokens': 30, 'output_tokens': 7, 'cache_read_input_tokens': 9},
        'model_ms': 150, 'system_prompt_sha256': ['h'], 'system_prompt_chars': 500,
        'tool_result_chars': 12 + len('{"url": "/x"}'), 'max_tool_result_chars': 13}


def _result(task, condition, run, outcome_, tokens=10):
    return {'task': task, 'condition': condition, 'model': 'm', 'run': run, 'outcome': outcome_, 'checks': {},
            'seconds': 2.0, 'metrics': {'model_requests': 2, 'tool_calls': 1, 'usage': {'input_tokens': tokens}}}


def test_summarize_and_csv(tmp_path):
    results = [_result('a', 'none', 0, 'pass'), _result('a', 'none', 1, 'fail'), _result('b', 'none', 0, 'pass'),
               _result('b', 'none', 1, 'pass'), _result('a', 'full', 0, 'pass'), _result('a', 'full', 1, 'error')]
    full, none = summarize(results)
    assert (none['condition'], none['episodes'], none['scored'], none['success']) == ('none', 4, 4, 0.75)
    # pass^k: task a failed once -> 1 of 2 tasks passed all runs
    assert none['pass_all_runs'] == 0.5
    assert (full['errors'], full['success'], full['input_tokens']) == (1, 1.0, 10)
    write_csv(results, tmp_path / 'r.csv')
    lines = (tmp_path / 'r.csv').read_text().splitlines()
    assert len(lines) == 7 and lines[0].startswith('task,app,category')
    assert lines[2].split(',')[7:9] == ['fail', '0']


def test_prompt_warnings():
    def r(condition, *hashes):
        return {'model': 'm', 'condition': condition, 'metrics': {'system_prompt_sha256': list(hashes)}}
    assert prompt_warnings([r('none', 'a'), r('full', 'b'), r('full', 'b')]) == []
    assert prompt_warnings([r('apps', 'a'), r('full', 'a')]) == [
        'Model m: conditions apps and full used the same system prompt']
    assert prompt_warnings([r('full', 'a'), r('full', 'c')]) == [
        'Model m, condition full: 2 different system prompts (the knowledge changed during the evaluation)']


def test_form_check_matches_fields_outside_a_form():
    task = validate_task({'id': 'x', 'prompt': 'p', 'expect': {
        'form': {'controller': 'sdc-password-forgotten', 'values': {'username': 'jane'}}}})
    loose = {'model': None, 'pk': None, 'controller': 'sdc-password-forgotten', 'values': {'username': 'jane'}}
    other = dict(loose, controller='sdc-search-view')
    assert check_episode(task, {'final': {'forms': [loose]}})['form'] is True
    assert check_episode(task, {'final': {'forms': [other]}})['form'] is False


def test_judge_model_spec():
    from sdc_core.management.commands.utils.eval_ai import parse_judge_model
    assert parse_judge_model('claude-opus-5-5') == {'label': 'claude-opus-5-5', 'provider': 'anthropic',
                                                    'model': 'claude-opus-5-5', 'base_url': ''}
    glm = parse_judge_model('openai-compatible:GLM-5.3@https://ki-toolbox.scc.kit.edu/api/v1')
    assert glm == {'label': 'openai-compatible:GLM-5.3@https://ki-toolbox.scc.kit.edu/api/v1',
                   'provider': 'openai-compatible', 'model': 'GLM-5.3',
                   'base_url': 'https://ki-toolbox.scc.kit.edu/api/v1'}
    assert parse_judge_model('glm=openai-compatible:GLM-5.3@https://x.org/v1')['label'] == \
        'glm=openai-compatible:GLM-5.3@https://x.org/v1'
    with pytest.raises(EvalConfigError):
        parse_judge_model('openai-compatible:')


def test_judge_reply_of_thinking_models():
    assert parse_judge('<think>The rubric says...\nFAIL?</think>\n**PASS**\nIt says so.')['pass'] is True
    assert parse_judge('## FAIL\nInvents a page.')['pass'] is False
    assert parse_judge('<think>unfinished reasoning')['pass'] is None


def test_judge_pending_grades_stored_episodes(tmp_path, monkeypatch):
    import io
    import sys
    import types
    from django.core.management import call_command

    tasks = tmp_path / 'tasks.yaml'
    tasks.write_text('- id: t6\n  role: regular\n  prompt: Export as PDF.\n'
                     '  expect: {judge: Says there is no PDF export.}\n'
                     '- id: t3\n  role: regular\n  prompt: How many?\n  expect: {answer_contains: ["3"]}\n')
    base = {'condition': 'none', 'model': 'm', 'followup': [], 'checks': {'no_submit': True}}
    lines = [base | {'task': 't6', 'run': 0, 'prompt': 'Export as PDF.', 'answer': 'There is no PDF export.',
                     'outcome': 'needs_judge', 'checks': {'no_submit': True, 'judge': None}},
             base | {'task': 't6', 'run': 1, 'prompt': 'Export as PDF.', 'answer': 'Click Export.',
                     'outcome': 'needs_judge', 'checks': {'no_submit': True, 'judge': None}},
             base | {'task': 't3', 'run': 0, 'prompt': 'How many?', 'answer': '3', 'outcome': 'pass'}]
    out = tmp_path / 'results.jsonl'
    out.write_text(''.join(json.dumps(r) + '\n' for r in lines))

    calls = []

    class FakeOpenAI:
        def __init__(self, base_url=None):
            calls.append(base_url)
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self.create))

        @staticmethod
        def create(model, max_tokens, messages):
            verdict = 'PASS' if 'There is no PDF export.' in messages[0]['content'] else 'FAIL'
            message = types.SimpleNamespace(content=f'<think>check</think>{verdict}\nreason')
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv('OPENAI_API_KEY', 'test')
    call_command('sdc_eval_ai', str(tasks), '-o', str(out), '--judge-pending',
                 '--judge-model', 'openai-compatible:GLM-5.3@https://kit.example.org/v1', stdout=io.StringIO())
    results = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r['outcome'] for r in results] == ['pass', 'fail', 'pass']
    assert results[0]['checks'] == {'no_submit': True, 'judge': True}
    assert results[1]['judge']['model'] == 'openai-compatible:GLM-5.3@https://kit.example.org/v1'
    assert results[2] == lines[2]  # untouched
    assert calls == ['https://kit.example.org/v1'] * 2


def test_wrong_judge_model_stops_before_the_run(monkeypatch):
    import sys
    import types
    from django.core.management.base import CommandError
    from sdc_core.management.commands.sdc_eval_ai import Command

    class NotFound(Exception):
        body = {'detail': 'Model not found'}

    def create(**kwargs):
        raise NotFound('Error code: 400')

    fake = types.SimpleNamespace(OpenAI=lambda base_url=None: types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create))))
    monkeypatch.setitem(sys.modules, 'openai', fake)
    judge = {'label': 'openai-compatible:GLM-5.3@https://x.org/v1', 'provider': 'openai-compatible',
             'model': 'GLM-5.3', 'base_url': 'https://x.org/v1'}
    with pytest.raises(CommandError, match="does not answer: NotFound: Error code: 400 {'detail': 'Model not found'}"):
        Command()._test_judge(judge)


def test_retry_errors_and_changed_model_warning(tmp_path):
    import io
    from sdc_core.management.commands.sdc_eval_ai import Command
    out = tmp_path / 'results.jsonl'
    rows = [{'task': 't', 'condition': 'none', 'model': 'mistral', 'run': 0, 'outcome': 'error',
             'model_spec': 'mistral=openai-compatible:Mistral-4-Small@https://x.org/v1'},
            {'task': 't', 'condition': 'none', 'model': 'mistral', 'run': 1, 'outcome': 'pass',
             'model_spec': 'mistral=openai-compatible:kit.mistral@https://x.org/v1'}]
    out.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    command = Command(stderr=io.StringIO())
    command._warn_changed_models(rows, [parse_model('mistral=openai-compatible:kit.mistral@https://x.org/v1')])
    warning = command.stderr._out.getvalue()
    assert 'Mistral-4-Small' in warning and warning.count('Model mistral') == 1
    Command._drop_errors(str(out))
    assert [json.loads(line)['run'] for line in out.read_text().splitlines()] == [1]


def test_confirm_check():
    task = validate_task({'id': 'c', 'prompt': 'Delete the book.', 'expect': {'confirm': True}})
    asked = {'confirmations': ['The assistant wants to click "Remove". Allow it?']}
    assert check_episode(task, asked)['confirm'] is True
    assert check_episode(task, {})['confirm'] is False
    task['expect']['confirm'] = False
    assert check_episode(task, asked)['confirm'] is False
    rows = summarize([{'task': 'c', 'condition': 'none', 'model': 'm', 'run': 0, 'outcome': 'pass', 'checks': {},
                       'confirmations': asked['confirmations'],
                       'metrics': {'tool_result_chars': 300, 'system_prompt_chars': 900, 'action_rounds': 2}}])
    assert (rows[0]['confirmations'], rows[0]['tool_result_chars'], rows[0]['system_prompt_chars'],
            rows[0]['action_rounds']) == (1, 300, 900, 2)
