"""``sdc_eval_ai --agent mcp``: tasks, checks, the agent loop with a scripted model, tokens and the oracle."""
import contextlib
import io
import json
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client, override_settings  # noqa: E402

from main_test.models import Author  # noqa: E402
from sdc_core.management.commands import sdc_eval_ai  # noqa: E402
from sdc_core.management.commands.utils import eval_mcp  # noqa: E402
from sdc_core.management.commands.utils.eval_ai import (  # noqa: E402
    EvalConfigError, check_episode, outcome, validate_task)
from sdc_core.management.commands.utils.eval_mcp import (  # noqa: E402
    McpError, OracleSession, ToolRunner, TransportError, connect, evaluate_records, mcp_metrics, model_tools,
    parse_mcp_condition, parse_mcp_model, parse_privileges, run_episode)

User = get_user_model()
URL = '/sdc_mcp/'
BASE = dict(SDC_AI_SKILL_DATA_FILE='missing.json', SDC_AI_SKILL_FILE='missing.md')
OPS = {'confirm': 'deny', 'episode_timeout': 30, 'max_turns': 40}


@pytest.fixture(autouse=True)
def enabled(tmp_path):
    (tmp_path / 'recipe.md').write_text('# Recipe\nDo it like this.', encoding='utf-8')
    mcp = {'enabled': True, 'instructions_extra': 'Always finish what you start.',
           'resources': [{'name': 'recipe', 'path': 'recipe.md', 'title': 'Recipe'}]}
    with override_settings(BASE_DIR=tmp_path, SDC_MCP=mcp, **BASE):
        yield


class ClientTransport:
    """The interface of ``HttpTransport`` on the Django test client (no server)."""

    def __init__(self, secret):
        self.client = Client(headers={'Authorization': f'Bearer {secret}'})
        self.version, self.counter = None, 0

    def _post(self, message):
        return self.client.post(URL, json.dumps(message), content_type='application/json')

    def call(self, method, params=None):
        self.counter += 1
        response = self._post({'jsonrpc': '2.0', 'id': self.counter, 'method': method, 'params': params or {}})
        if response.status_code != 200:
            raise TransportError(f'HTTP {response.status_code}', response.status_code)
        data = json.loads(response.content)
        if 'error' in data:
            raise McpError(data['error']['message'])
        return data['result']

    def notify(self, method):
        assert self._post({'jsonrpc': '2.0', 'method': method}).status_code == 202


class ScriptedSession(OracleSession):
    """A model that follows a script and keeps what the harness sent it (the tool results)."""

    def __init__(self, reference, instructions=None, tools=None):
        super().__init__(reference)
        self.instructions, self.tools, self.prompts, self.results = instructions, tools, [], []

    def add_user(self, text):
        self.prompts.append(text)

    def add_tool_results(self, results):
        self.results += results


@pytest.fixture
def jane(db):
    return User.objects.create_user(username='jane', password='pw')


def _secret(user, *privileges):
    from sdc_core import api_tokens
    return api_tokens.create_token(user, 'eval', list(privileges))[1]


def _episode(reference, secret, prompts=('Do it.',), **ops):
    sessions = []

    def factory(instructions, tools):
        sessions.append(ScriptedSession(reference, instructions, tools))
        return sessions[0]
    episode = run_episode(factory, ClientTransport(secret), secret, list(prompts), OPS | ops)
    return episode, (sessions[0] if sessions else None)


def _state(fixtures=None, users=None, tokens=None):
    """The state script in the test database (the command runs it in the evaluation server's project)."""
    out = io.StringIO()
    env = {'SDC_EVAL_FIXTURES': json.dumps(fixtures), 'SDC_EVAL_USERS': json.dumps(users or {}),
           'SDC_EVAL_TOKENS': json.dumps(tokens or {})}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        with contextlib.redirect_stdout(out):
            exec(sdc_eval_ai.STATE_SCRIPT, {})
    finally:
        for k, v in old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    line = next(l for l in out.getvalue().splitlines() if l.startswith('SDC_EVAL_STATE '))
    return json.loads(line[len('SDC_EVAL_STATE '):])


# ------------------------------------------------------------------------------------------------- tasks
def _task(**extra):
    return {'id': 't', 'prompt': 'p', 'expect': {'answer_contains': ['x']}} | extra


def test_task_keys_and_agent_inference():
    assert validate_task(_task())['agent'] is None
    assert validate_task(_task(agent='mcp', privileges=['read']))['privileges'] == ['read']
    assert validate_task(_task(expect={'tools_used': ['model_load']}))['agent'] == 'mcp'
    assert validate_task(_task(expect={'controller': 'x'}))['agent'] == 'browser'
    assert validate_task(_task(privileges=['model:*:read']))['agent'] == 'mcp'
    records = {'records': [{'model': 'Author', 'filter': {'name': 'A'}, 'count': {'min': 1}, 'fields': {'age': 3}}]}
    assert validate_task(_task(expect=records))['agent'] == 'mcp'


@pytest.mark.parametrize('task, msg', [
    (_task(agent='robot'), 'agent must be'),
    (_task(privileges='read'), 'privileges must be'),
    (_task(agent='browser', privileges=['read']), 'only apply to the agent mcp'),
    (_task(agent='browser', expect={'tools_used': ['a']}), 'do not apply'),
    (_task(agent='mcp', expect={'path': []}), 'do not apply'),
    (_task(expect={'path': [], 'tools_used': ['a']}), 'cannot be combined'),
    (_task(expect={'records': [{'filter': {}}]}), 'records entry'),
    (_task(expect={'records': [{'model': 'A', 'count': 'many'}]}), 'records count'),
    (_task(expect={'records': [{'model': 'A', 'count': {'least': 1}}]}), 'records count'),
    (_task(expect={'tools_used': 'model_load'}), 'tools_used must be'),
    (_task(expect={'tools_not_used': [3]}), 'tools_not_used must be'),
    (_task(expect={'max_tool_errors': -1}), 'max_tool_errors'),
])
def test_invalid_mcp_tasks(task, msg):
    with pytest.raises(EvalConfigError, match=msg):
        validate_task(task)


def test_tasks_of_the_other_agent_are_skipped_with_a_note():
    command = sdc_eval_ai.Command(stdout=io.StringIO())
    tasks = [validate_task(_task(id='a')), validate_task(_task(id='m', agent='mcp')),
             validate_task(_task(id='b', agent='browser'))]
    assert [t['id'] for t in command._tasks_of_agent(tasks, 'mcp')] == ['a', 'm']
    assert 'Skipped 1 tasks for the other agent: b' in command.stdout.getvalue()
    assert [t['id'] for t in command._tasks_of_agent(tasks, 'browser')] == ['a', 'b']
    with pytest.raises(EvalConfigError):
        command._tasks_of_agent(tasks[1:2], 'browser')


# ------------------------------------------------------------------------------------------------ checks
def _calls(*names, errors=()):
    return [{'name': n, 'arguments': {}, 'is_error': n in errors} for n in names]


def test_tools_checks():
    task = validate_task(_task(expect={'tools_used': ['model_load', ['a_create', 'a_update']],
                                       'tools_not_used': ['a_delete', ['x', 'y']], 'max_tool_errors': 2}))
    good = {'answer': '', 'tool_calls': _calls('model_load', 'a_update', 'a_update', errors=('a_update',))}
    # tools_used and records are not about the database: the default of allow_db_changes stays false without records
    checks = check_episode(task, good)
    assert checks['tools_used'] and checks['tools_not_used'] and checks['max_tool_errors']
    assert checks['db_unchanged']
    assert not check_episode(task, {'tool_calls': _calls('model_load')})['tools_used']
    assert not check_episode(task, good | {'tool_calls': good['tool_calls'] + _calls('y')})['tools_not_used']
    two_errors = good['tool_calls'] + _calls('model_load', errors=('model_load',))  # three errors
    assert not check_episode(task, good | {'tool_calls': two_errors})['max_tool_errors']
    assert not check_episode(task, {})['tools_used']
    assert outcome(check_episode(task, good)) == 'pass'


def test_records_check_allows_db_changes_by_default():
    task = validate_task(_task(expect={'records': [{'model': 'Author', 'filter': {'name': 'A'}}]}))
    episode = {'records': [{'count': 1, 'fields': {}}], 'db_changes': {'main_test.author': {}}}
    assert check_episode(task, episode)['records'] and 'db_unchanged' not in check_episode(task, episode)
    stricter = validate_task(_task(expect={'records': [{'model': 'Author'}], 'allow_db_changes': False}))
    assert not check_episode(stricter, episode)['db_unchanged']
    assert not check_episode(task, {'records': []})['records']


def test_evaluate_records(db):
    Author.objects.create(name='Ada', age=36)
    Author.objects.create(name='Ada', age=40)
    Author.objects.create(name='Bob', age=7)
    specs = [{'model': 'Author', 'filter': {'name': 'Ada'}, 'count': 2, 'fields': {'age': 36}},
             {'model': 'main_test.Author', 'filter': {'age__lt': 10}, 'fields': {'name': 'Bob'}},
             {'model': 'Author', 'filter': {'name': 'Ada'}, 'count': 1},
             {'model': 'Author', 'filter': {'name': 'Zed'}},
             {'model': 'Author', 'filter': {'name': 'Ada'}, 'count': {'min': 1, 'max': 3}, 'fields': {'age': 36}},
             {'model': 'Nothing'}, {'model': 'Author', 'filter': {'color': 1}}]
    results = evaluate_records(specs)
    verdicts = [eval_mcp.record_matches(s, r) for s, r in zip(specs, results)]
    assert verdicts == [True, True, False, False, True, False, False]
    assert results[0] == {'model': 'Author', 'filter': {'name': 'Ada'}, 'count': 2, 'fields': {'age': 36}}
    assert 'unknown model' in results[5]['error'] and 'FieldError' in results[6]['error']
    # A field mismatch fails: the first match (lowest pk) is Ada, 36
    assert not eval_mcp.record_matches({'model': 'Author', 'fields': {'age': 40}},
                                       evaluate_records([{'model': 'Author', 'filter': {'name': 'Ada'},
                                                          'fields': {'age': 40}}])[0])


# ---------------------------------------------------------------------------------------------- conditions
def test_conditions_and_models():
    full, none = parse_mcp_condition('full'), parse_mcp_condition('x=none')
    assert full['mcp'] == {'enabled': True} and none['label'] == 'x'
    assert none['mcp'] == {'enabled': True, 'instructions_extra': None, 'resources': []}
    for bad in ('apps', 'index', 'full:SDC_SKILL.md'):
        with pytest.raises(EvalConfigError, match='source must be one of full, none'):
            parse_mcp_condition(bad)
    assert parse_mcp_model('oracle')['spec'] == 'oracle'
    assert parse_mcp_model('anthropic:claude-opus-5-5')['settings']['SDC_AI_MODEL'] == 'claude-opus-5-5'
    assert parse_privileges('read, account:write,') == ['read', 'account:write']


def test_settings_source_overrides_sdc_mcp():
    source = eval_mcp.mcp_settings_source('SdcTest.settings', parse_mcp_condition('none'))
    scope = {}
    with override_settings(SDC_MCP={'enabled': False, 'name': 'keep'}):
        exec(source.split('\n', 2)[2], {'SDC_MCP': {'enabled': False, 'name': 'keep', 'instructions_extra': 'x'}}, scope)
    assert scope['SDC_MCP'] == {'enabled': True, 'name': 'keep', 'instructions_extra': None, 'resources': []}


def test_conditions_change_the_instructions(jane):
    secret = _secret(jane, 'model:*:read')
    full, _ = connect(ClientTransport(secret))
    assert 'Always finish what you start.' in full and 'sdc://app/recipe' in full
    with override_settings(SDC_MCP={'enabled': True, 'instructions_extra': None, 'resources': []}):
        none, _ = connect(ClientTransport(secret))
    assert 'Always finish' not in none and 'sdc://app/recipe' not in none and 'model_load' in none


# ------------------------------------------------------------------------------------------ tool conversion
def test_tool_conversion(jane):
    _, tools = connect(ClientTransport(_secret(jane, 'model:*:read', 'model:Author:write')))
    converted = model_tools(tools)
    names = [t['name'] for t in converted]
    assert names[-2:] == ['resources_list', 'resources_read'] and 'model_load' in names and 'author_create' in names
    load = next(t for t in converted if t['name'] == 'model_load')
    assert load['input_schema']['properties']['model'] and load['description'] and set(load) == {
        'name', 'description', 'input_schema'}
    assert eval_mcp.needs_confirmation(next(t for t in tools if t['name'] == 'author_create'))
    assert not eval_mcp.needs_confirmation(next(t for t in tools if t['name'] == 'model_load'))
    assert not eval_mcp.needs_confirmation(None) and eval_mcp.needs_confirmation({'name': 'x'})


# ------------------------------------------------------------------------------------------------ the loop
def test_read_episode_with_resources(jane):
    Author.objects.create(name='Ada', age=36)
    reference = [{'resources_list': {}}, {'resources_read': {'uri': 'sdc://app/recipe'}},
                 {'resources_read': {'uri': 'sdc://app/nothing'}}, {'model_load': {'model': 'Author'}},
                 {'answer': 'There is one author.'}]
    episode, session = _episode(reference, _secret(jane, 'model:*:read'), ('How many?', 'Thanks.'))
    assert 'Always finish' in session.instructions and session.prompts == ['How many?', 'Thanks.']
    assert [c['name'] for c in episode['tool_calls']] == ['resources_list', 'resources_read', 'resources_read',
                                                         'model_load']
    assert [c['is_error'] for c in episode['tool_calls']] == [False, False, True, False]
    results = {r[0]: r[1] for r in session.results}
    assert 'sdc://app/recipe' in results['oracle_1'] and 'Do it like this.' in results['oracle_2']
    assert 'Resource not found' in results['oracle_3'] and '"Ada"' in results['oracle_4']
    # The follow-up is answered by the oracle's default after the reference is used up
    assert episode['answers'] == ['There is one author.', 'Done.'] and episode['answer'] == 'Done.'
    assert episode['turns'] == 6
    assert any('Ada' in text for text in episode['tool_results'])
    metrics = mcp_metrics(episode)
    assert metrics['tool_calls'] == 4 and metrics['tool_errors'] == 1 and metrics['model_requests'] == 6
    assert metrics['tool_calls_by_name']['resources_read'] == 2 and metrics['system_prompt_chars'] > 100


@pytest.mark.parametrize('confirm, created, declined', [('deny', 0, True), ('allow', 1, False)])
def test_confirmations(jane, confirm, created, declined):
    reference = [{'author_create': {'name': 'Eve', 'age': 20}}, {'model_load': {'model': 'Author'}},
                 {'answer': 'done'}]
    episode, session = _episode(reference, _secret(jane, 'model:*:read', 'model:*:write'), confirm=confirm)
    assert Author.objects.filter(name='Eve').count() == created
    assert len(episode['confirmations']) == 1 and 'author_create' in episode['confirmations'][0]
    assert bool(episode['tool_calls'][0].get('declined')) == declined
    first = session.results[0]
    assert (first[1] == 'The user declined this action.') == declined and first[2] is False
    # Reading never asks
    assert 'declined' not in episode['tool_calls'][1] and len(episode['confirmations']) == 1


def test_errors_of_tools_are_results_not_failures(jane):
    reference = [{'model_load': {'model': 'Nothing'}}, {'nope': {}}, {'account_get': ['not a dict']},
                 {'answer': 'Sorry.'}]
    episode, session = _episode(reference, _secret(jane, 'model:*:read'))
    assert 'error' not in episode
    assert [c['is_error'] for c in episode['tool_calls']] == [True, True, True]
    assert episode['tool_calls'][2]['invalid'] and 'Unknown tool' in session.results[1][1]
    assert mcp_metrics(episode)['invalid_tool_inputs'] == 1


def test_max_turns(jane):
    reference = [{'model_load': {'model': 'Author'}}] * 5 + [{'answer': 'late'}]
    episode, _ = _episode(reference, _secret(jane, 'model:*:read'), max_turns=3)
    assert episode['turns'] == 3 and episode['max_turns_reached'] and len(episode['tool_calls']) == 3
    assert episode['answer'] == '' and 'error' not in episode
    episode, _ = _episode(reference, _secret(jane, 'model:*:read'), max_turns=6)
    assert not episode['max_turns_reached'] and episode['answer'] == 'late'


def test_a_bad_token_is_an_http_error_not_a_crash(jane):
    episode, _ = _episode([{'answer': 'x'}], 'sdc_not_a_token')
    assert 'TransportError' in episode['error'] and 'tool_calls' not in episode


def test_http_errors_of_tool_calls_are_recorded(jane):
    class Failing(ClientTransport):
        def call(self, method, params=None):
            if method == 'tools/call':
                raise TransportError('HTTP 403 from /sdc_mcp/', 403)
            return super().call(method, params)
    secret = _secret(jane, 'model:*:read')
    episode = run_episode(lambda i, t: OracleSession([{'model_load': {'model': 'Author'}}, {'answer': 'x'}]),
                          Failing(secret), secret, ['p'], OPS)
    assert episode['http_errors'] == [{'url': '/sdc_mcp/', 'status': 403}] and episode['tool_calls'][0]['is_error']


def test_oracle_replays_a_reference_and_passes_its_checks(jane, db):
    task = validate_task({
        'id': 'o', 'role': 'r', 'prompt': 'Create Eve.', 'privileges': ['read', 'model:Author:write'],
        'expect': {'records': [{'model': 'Author', 'filter': {'name': 'Eve'}, 'count': 1, 'fields': {'age': 20}}],
                   'tools_used': ['author_create'], 'tools_not_used': ['author_delete'], 'max_tool_errors': 0,
                   'answer_contains': ['created']},
        'reference': [{'author_create': {'name': 'Eve', 'age': 20}}, {'answer': 'I created Eve.'}]})
    secret = _secret(jane, 'model:*:read', 'model:Author:write')
    episode = run_episode(lambda i, t: OracleSession(task['reference']), ClientTransport(secret), secret,
                          ['Create Eve.'], OPS | {'confirm': 'allow'})
    episode['records'] = evaluate_records(task['expect']['records'])
    episode['db_changes'] = {'main_test.author': {}}
    checks = check_episode(task, episode)
    assert outcome(checks) == 'pass', checks
    # Declined: the record is missing
    Author.objects.all().delete()
    episode = run_episode(lambda i, t: OracleSession(task['reference']), ClientTransport(secret), secret,
                          ['Create Eve.'], OPS)
    episode['records'] = evaluate_records(task['expect']['records'])
    assert outcome(check_episode(task, episode)) == 'fail'


# --------------------------------------------------------------------------------------------- the provider
@pytest.mark.parametrize('provider', ['anthropic', 'openai-compatible'])
def test_consumer_session_reuses_the_assistants_provider(monkeypatch, provider):
    from sdc_core.consumers import SDCAiConsumer
    seen = []

    async def stream(self, id, final=False):
        seen.append((self._config('provider'), self._config('model'), self.system_prompt, self._tools(),
                     list(self.messages)))
        if len(seen) == 1:
            message = {'role': 'assistant', 'content': 'x'} if provider == 'anthropic' else {
                'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c1'}]}
            return {'text': '', 'stop': 'tool_use', 'message': message, 'usage': {'input_tokens': 3},
                    'tool_uses': [{'id': 'c1', 'name': 'model_load', 'input': {'model': 'Author'}}]}
        return {'text': 'ok', 'stop': 'end_turn', 'tool_uses': [], 'usage': None,
                'message': {'role': 'assistant', 'content': 'ok'}}
    monkeypatch.setattr(SDCAiConsumer, '_stream', stream)
    tools = [{'name': 'model_load', 'description': 'd', 'input_schema': {'type': 'object'}}]
    values = {'provider': provider, 'model': 'm1', 'base_url': '', 'effort': '', 'max_tokens': None}
    session = eval_mcp.consumer_session(values, 'SYSTEM', tools)

    async def go():
        session.add_user('hi')
        first = await session.step()
        session.add_tool_results([('c1', 'result text', True)])
        return first, await session.step()
    import asyncio
    first, second = asyncio.run(go())
    assert first['tool_uses'][0]['name'] == 'model_load' and second['text'] == 'ok'
    assert seen[0][:4] == (provider, 'm1', 'SYSTEM', tools)
    tool_message = seen[1][4][-1]
    if provider == 'anthropic':
        assert tool_message['content'] == [{'type': 'tool_result', 'tool_use_id': 'c1', 'is_error': True,
                                            'content': 'result text'}]
    else:
        assert tool_message == {'role': 'tool', 'tool_call_id': 'c1', 'content': 'Error: result text'}


# ------------------------------------------------------------------------- tokens, results and secrets
def test_tokens_per_role_from_privileges_and_presets(jane):
    User.objects.create_user(username='bob', password='pw')
    users = {'reader': {'username': 'jane', 'password': 'pw'}, 'writer': {'username': 'bob', 'password': 'pw'}}
    state = _state(None, users, {'reader': ['read'], 'writer': ['read', 'model:Author:write']})
    assert set(state['tokens']) == {'reader', 'writer'} and state['tokens']['reader'] != state['tokens']['writer']

    def names(role):
        return [t['name'] for t in connect(ClientTransport(state['tokens'][role]))[1]]
    assert 'model_load' in names('reader') and 'author_create' not in names('reader')
    assert 'author_create' in names('writer')
    # The token is not part of the snapshot: using it does not look like a database change
    assert 'sdc_core.apitoken' not in state['snapshot']
    # A second run replaces the token of the user instead of piling them up
    from sdc_core.models import ApiToken
    _state(None, users, {'reader': ['read']})
    assert ApiToken.objects.filter(user=jane, name='sdc_eval_ai').count() == 1
    assert _state(None, users, {})['tokens'] == {}


def test_state_script_rejects_unknown_privileges(jane):
    with pytest.raises(Exception, match='Unknown privilege'):
        _state(None, {'r': {'username': 'jane', 'password': 'pw'}}, {'r': ['model:*:bake']})


def _command(monkeypatch, reference, secrets, fail_with_secret=False):
    """The command with the server-side parts (state script, records, transport, model) run in-process."""
    command = sdc_eval_ai.Command(stdout=io.StringIO(), stderr=io.StringIO())
    monkeypatch.setattr(command, '_state', lambda env, fixtures, users, tokens=None: _state(fixtures, users, tokens))
    monkeypatch.setattr(command, '_records', lambda env, specs: evaluate_records(specs))

    def transport(base_url, secret):
        secrets.append(secret)
        return ClientTransport(secret)
    monkeypatch.setattr(command, '_transport', transport)

    def session(model, task, ops):
        def make(instructions, tools):
            if fail_with_secret:
                raise RuntimeError(f'cannot connect with {secrets[-1]}')
            return ScriptedSession(reference)
        return make
    monkeypatch.setattr(command, '_model_session', session)
    return command


def _run(command, task, **ops):
    ops = OPS | {'confirm': 'allow', 'fixtures': [], 'judge': None, 'mcp_privileges': 'read'} | ops
    users = {'regular': {'username': 'jane', 'password': 'pw'}}
    return command._episode_mcp('http://x', {}, task, 0, parse_mcp_condition('full'), parse_mcp_model('oracle'),
                                users, ops)


def test_an_episode_end_to_end_without_leaking_the_token(jane, monkeypatch):
    task = validate_task({
        'id': 'e2e', 'role': 'regular', 'prompt': 'Add Eve.', 'privileges': ['read', 'model:Author:write'],
        'expect': {'records': [{'model': 'Author', 'filter': {'name': 'Eve'}, 'fields': {'age': 20}}],
                   'tools_used': ['author_create'], 'answer_contains': ['added']},
        'reference': []})
    secrets = []
    reference = [{'resources_list': {}}, {'author_create': {'name': 'Eve', 'age': 20}}, {'answer': 'Eve was added.'}]
    result = _run(_command(monkeypatch, reference, secrets), task)
    assert result['outcome'] == 'pass', result
    assert result['agent'] == 'mcp' and result['privileges'] == ['read', 'model:Author:write']
    assert [c['name'] for c in result['tool_calls']] == ['resources_list', 'author_create']
    assert result['records'][0]['fields'] == {'age': 20} and result['confirmations'] and result['final'] is None
    assert list(result['db_changes']) == ['main_test.author']
    assert result['metrics']['tool_calls'] == 2 and result['answer'] == 'Eve was added.'
    assert len(secrets) == 1 and secrets[0].startswith('sdc_')
    assert secrets[0] not in json.dumps(result, default=str)


def test_the_default_privileges_come_from_the_option(jane, monkeypatch):
    task = validate_task({'id': 'd', 'role': 'regular', 'prompt': 'p', 'expect': {'tools_used': ['author_create']},
                          'agent': 'mcp'})
    result = _run(_command(monkeypatch, [{'author_create': {'name': 'x', 'age': 1}}, {'answer': 'a'}], []), task,
                  mcp_privileges='model:*:read,model:Author:write')
    assert result['privileges'] == ['model:*:read', 'model:Author:write'] and result['outcome'] == 'fail'
    result = _run(_command(monkeypatch, [{'author_create': {'name': 'x', 'age': 1}}, {'answer': 'a'}], []), task)
    assert result['privileges'] == ['read'] and result['tool_calls'][0]['is_error']
    assert Author.objects.count() == 1


def test_errors_do_not_contain_the_secret(jane, monkeypatch):
    task = validate_task({'id': 'x', 'role': 'regular', 'prompt': 'p', 'expect': {'tools_used': ['a']}})
    secrets = []
    result = _run(_command(monkeypatch, [], secrets, fail_with_secret=True), task)
    assert result['outcome'] == 'error' and 'cannot connect with' in result['error']
    assert secrets[0] not in json.dumps(result, default=str) and '***' in result['error']
    # A tool result that echoes the token is scrubbed too
    secret = _secret(jane, 'model:*:read')
    runner = ToolRunner(ClientTransport(secret), [], secrets=[secret])
    runner.transport.call = lambda *a, **k: {'content': [{'type': 'text', 'text': f'you sent {secret}'}]}
    text, _ = runner.run('whatever', {})
    assert secret not in text and secret not in json.dumps(runner.tool_results)


def test_the_command_has_the_new_options():
    from django.core.management import load_command_class
    parser = load_command_class('sdc_core', 'sdc_eval_ai').create_parser('manage.py', 'sdc_eval_ai')
    ops = parser.parse_args(['t.yaml'])
    assert (ops.agent, ops.mcp_privileges, ops.max_turns) == ('browser', 'read', 40)
    ops = parser.parse_args(['t.yaml', '--agent', 'mcp', '--max-turns', '5', '--mcp-privileges', 'full'])
    assert (ops.agent, ops.mcp_privileges, ops.max_turns) == ('mcp', 'full', 5)
