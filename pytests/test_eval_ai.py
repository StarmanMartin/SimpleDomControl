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
              {'dir': 'sent', 'data': {'event': 'action_results', 'results': [{'is_error': True}]}}]
    assert episode_metrics(records, frames) == {
        'model_requests': 2, 'action_rounds': 1, 'tool_calls': 2,
        'tool_calls_by_name': {'navigate': 1, 'model_get': 1}, 'invalid_tool_inputs': 1, 'tool_errors': 1,
        'request_errors': 0, 'usage': {'input_tokens': 30, 'output_tokens': 7, 'cache_read_input_tokens': 9},
        'model_ms': 150, 'system_prompt_sha256': ['h'], 'system_prompt_chars': 500}


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
