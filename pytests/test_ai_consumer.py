import json
import os
from types import SimpleNamespace

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from asgiref.sync import async_to_sync  # noqa: E402
from channels.testing import WebsocketCommunicator  # noqa: E402
from django.core.cache import cache  # noqa: E402
from django.test import override_settings  # noqa: E402

from sdc_core.consumers import AI_TOOLS, SDCAiConsumer  # noqa: E402

AI = dict(SDC_AI_ASSISTANT=True, SDC_AI_PROVIDER='anthropic', SDC_AI_TOKEN_FROM_SYSTEM=True,
          SDC_AI_REQUIRE_LOGIN=True, SDC_AI_ALLOWED_GROUPS=None, SDC_AI_MAX_REQUESTS_PER_USER=None,
          SDC_AI_MODEL='claude-opus-5-5', SDC_AI_BASE_URL='', SDC_AI_EFFORT='medium')


def _user(pk=1, authenticated=True, staff=False):
    return SimpleNamespace(pk=pk, is_authenticated=authenticated, is_staff=staff, is_superuser=False)


def _tool_use(id, name, **tool_input):
    return SimpleNamespace(type='tool_use', id=id, name=name, input=tool_input)


class FakeStream:
    def __init__(self, chunks, stop_reason, tool_uses=()):
        self.chunks, self.stop_reason, self.tool_uses = chunks, stop_reason, list(tool_uses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    @property
    def text_stream(self):
        async def gen():
            for c in self.chunks:
                yield c
        return gen()

    async def get_final_message(self):
        return SimpleNamespace(stop_reason=self.stop_reason,
                               content=[SimpleNamespace(type='thinking', thinking=''),
                                        SimpleNamespace(type='text', text=''.join(self.chunks))] + self.tool_uses)


class FakeClient:
    """Answers with ``script`` (one ``(chunks, stop_reason, tool_uses)`` per request; the last one repeats)."""

    def __init__(self, chunks=('Hel', 'lo'), stop_reason='end_turn', script=None):
        self.calls = []
        self.script = script or [(chunks, stop_reason, ())]
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **params):
        # Copy: the consumer keeps appending to the same list
        self.calls.append(params | {'messages': list(params['messages'])})
        return FakeStream(*self.script[min(len(self.calls), len(self.script)) - 1])


async def _session(user, events, client=None, monkeypatch=None, with_config=False):
    """
    Connects, sends ``events`` and returns ``(connected, [received messages])``; ``ai_config`` messages are left
    out unless ``with_config``.
    """
    if client is not None:
        monkeypatch.setattr(SDCAiConsumer, '_client', lambda self: client)
    communicator = WebsocketCommunicator(SDCAiConsumer.as_asgi(), '/sdc_ws/ai')
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    received = []

    async def drain():
        while not await communicator.receive_nothing(timeout=0.2):
            output = await communicator.receive_output()
            if output['type'] == 'websocket.close':
                received.append({'type': 'close', 'code': output.get('code')})
                return False
            received.append(json.loads(output['text']))
        return True

    if await drain():
        for event in events:
            await communicator.send_json_to(event)
            if not await drain():
                break
        await communicator.disconnect()
    return connected, [m for m in received if with_config or m['type'] != 'ai_config']


def run(*args, **kwargs):
    return async_to_sync(_session)(*args, **kwargs)


def test_prompt_streams_answer_and_keeps_history(monkeypatch):
    client = FakeClient()
    with override_settings(**AI):
        _, received = run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Hi'},
                                    {'event': 'prompt', 'id': 2, 'prompt': 'Again'}], client, monkeypatch)
    assert [m['type'] for m in received] == ['ai_delta', 'ai_delta', 'ai_answer'] * 2
    assert received[2] == {'type': 'ai_answer', 'id': 1, 'text': 'Hello', 'stop_reason': 'end_turn',
                           'is_error': False}
    first, second = client.calls
    assert first['model'] == 'claude-opus-5-5'
    assert first['fallbacks'] == 'default' and first['betas'] == ['server-side-fallback-2026-07-01']
    assert first['output_config'] == {'effort': 'medium'}
    assert first['system'][0]['text'].startswith('You are the assistant of this website')
    assert 'https://simpledomcontrol.readthedocs.io/en/latest/' in first['system'][0]['text']
    # SdcModels are read-only for the assistant
    assert [t['name'] for t in first['tools']] == ['navigate', 'read_page', 'fill_form', 'model_get', 'model_load']
    assert all(t['eager_input_streaming'] for t in first['tools'])
    assert 'tool_choice' not in first
    # The second request carries the first answer with all of its content blocks
    assert [m['role'] for m in second['messages']] == ['user', 'assistant', 'user']
    assert [b.type for b in second['messages'][1]['content']] == ['thinking', 'text']


def test_anonymous_rejected_with_system_token(monkeypatch):
    with override_settings(**AI | {'SDC_AI_REQUIRE_LOGIN': False}):
        _, received = run(_user(authenticated=False), [], FakeClient(), monkeypatch)
    assert received[0]['type'] == 'error' and 'log in' in received[0]['msg']
    assert received[1] == {'type': 'close', 'code': 4403}


def test_disabled_assistant_rejected(monkeypatch):
    with override_settings(**AI | {'SDC_AI_ASSISTANT': False}):
        _, received = run(_user(), [], FakeClient(), monkeypatch)
    assert received[0]['type'] == 'error' and 'disabled' in received[0]['msg']


def test_allowed_groups(monkeypatch):
    with override_settings(**AI | {'SDC_AI_ALLOWED_GROUPS': ['Editor']}):
        _, received = run(_user(staff=True), [{'event': 'prompt', 'id': 1, 'prompt': 'Hi'}], FakeClient(),
                          monkeypatch)
    assert received[-1]['type'] == 'ai_answer'  # staff always allowed


def test_user_token_required_and_used(monkeypatch):
    client = FakeClient()
    with override_settings(**AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False}):
        _, received = run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Hi'},
                                    {'event': 'set_config', 'token': 'sk-user'},
                                    {'event': 'prompt', 'id': 2, 'prompt': 'Hi'}], client, monkeypatch)
    assert received[0]['type'] == 'error' and received[0]['scope'] == 'token'
    assert received[-1]['type'] == 'ai_answer' and received[-1]['id'] == 2


def test_config_read_only_with_system_token(monkeypatch):
    with override_settings(**AI):
        _, received = run(_user(), [{'event': 'set_config', 'token': 'sk-user', 'model': 'x'}], FakeClient(),
                          monkeypatch, with_config=True)
    assert received[0]['type'] == 'ai_config'
    assert received[0]['editable'] is False and received[0]['allow_base_url'] is False
    assert received[0]['model'] == 'claude-opus-5-5' and received[0]['has_token'] is True
    assert received[1]['type'] == 'error' and '403' in received[1]['msg']


def test_user_config_is_used(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr('sdc_core.consumers._ai_check_public_url', _no_check)
    config = {'event': 'set_config', 'token': 'sk-user', 'model': 'claude-sonnet-5-5', 'effort': 'low',
              'max_tokens': '2000', 'base_url': 'https://proxy.example.com'}
    with override_settings(**AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False}):
        _, received = run(_user(), [config, {'event': 'set_config', 'model': 'claude-haiku-5-5'},
                                    {'event': 'prompt', 'id': 1, 'prompt': 'Hi'}],
                          client, monkeypatch, with_config=True)
    after_set = received[1]
    assert after_set['editable'] and after_set['has_token'] and 'token' not in after_set
    assert (after_set['model'], after_set['effort'], after_set['max_tokens'], after_set['base_url']) == \
           ('claude-sonnet-5-5', 'low', 2000, 'https://proxy.example.com')
    # A second set_config replaces the settings but keeps the key when its field is empty
    assert received[2]['has_token'] and received[2]['model'] == 'claude-haiku-5-5'
    assert received[2]['effort'] == 'medium' and received[2]['base_url'] == ''
    call = client.calls[0]
    assert call['model'] == 'claude-haiku-5-5' and call['max_tokens'] == 16000
    assert 'fallbacks' not in call  # not a fallback-capable model


async def _no_check(url):
    return None


def test_invalid_config_is_rejected(monkeypatch):
    with override_settings(**AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False}):
        _, received = run(_user(), [{'event': 'set_config', 'model': 'a b'},
                                    {'event': 'set_config', 'effort': 'extreme'},
                                    {'event': 'set_config', 'max_tokens': '0'},
                                    {'event': 'set_config', 'base_url': 'http://example.com'},
                                    {'event': 'set_config', 'base_url': 'https://127.0.0.1:8000'},
                                    {'event': 'set_config', 'base_url': 'https://localhost'}],
                          FakeClient(), monkeypatch)
    assert [m['scope'] for m in received] == ['settings'] * 6
    assert 'public' in received[4]['msg'] and 'public' in received[5]['msg']


def test_user_base_url_can_be_disabled(monkeypatch):
    monkeypatch.setattr('sdc_core.consumers._ai_check_public_url', _no_check)
    with override_settings(**AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False, 'SDC_AI_ALLOW_USER_BASE_URL': False}):
        _, received = run(_user(), [{'event': 'set_config', 'base_url': 'https://proxy.example.com'}],
                          FakeClient(), monkeypatch, with_config=True)
    assert received[0]['allow_base_url'] is False
    assert received[1]['type'] == 'error' and 'not allowed' in received[1]['msg']


def test_daily_limit(monkeypatch):
    cache.clear()
    with override_settings(**AI | {'SDC_AI_MAX_REQUESTS_PER_USER': 1}):
        _, received = run(_user(pk=42), [{'event': 'prompt', 'id': 1, 'prompt': 'Hi'},
                                         {'event': 'prompt', 'id': 2, 'prompt': 'Hi'}], FakeClient(), monkeypatch)
    assert received[-2]['type'] == 'ai_answer'
    assert received[-1]['type'] == 'error' and 'limit' in received[-1]['msg']


def test_refusal_is_not_kept(monkeypatch):
    client = FakeClient(stop_reason='refusal')
    with override_settings(**AI):
        _, received = run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Hi'},
                                    {'event': 'prompt', 'id': 2, 'prompt': 'Next'}], client, monkeypatch)
    assert [m['type'] for m in received].count('error') == 2
    assert [m['role'] for m in client.calls[1]['messages']] == ['user']


LOAD = _tool_use('t1', 'model_load', model='Author')
NAV = _tool_use('t2', 'navigate', path='/~main-view')


def test_actions_are_sent_and_results_continue_the_answer(monkeypatch):
    client = FakeClient(script=[(('Let me look. ',), 'tool_use', [LOAD, NAV]), (('There are 2.',), 'end_turn', ())])
    with override_settings(**AI):
        _, received = run(_user(), [
            {'event': 'prompt', 'id': 1, 'prompt': 'How many authors?'},
            {'event': 'action_results', 'id': 1, 'results': [
                {'tool_use_id': 't2', 'content': '/~main-view'},
                {'tool_use_id': 't1', 'content': [{'id': 1}, {'id': 2}]}]},
        ], client, monkeypatch)
    actions = next(m for m in received if m['type'] == 'ai_actions')
    assert actions['actions'] == [{'tool_use_id': 't1', 'name': 'model_load', 'input': {'model': 'Author'}},
                                  {'tool_use_id': 't2', 'name': 'navigate', 'input': {'path': '/~main-view'}}]
    assert received[-1]['type'] == 'ai_answer'
    assert received[-1]['text'] == 'Let me look. There are 2.'
    results = client.calls[1]['messages'][-1]
    assert results['role'] == 'user'
    # One block per tool use, in the order of the tool uses; non-string content is sent as JSON
    assert results['content'] == [
        {'type': 'tool_result', 'tool_use_id': 't1', 'is_error': False, 'content': '[{"id": 1}, {"id": 2}]'},
        {'type': 'tool_result', 'tool_use_id': 't2', 'is_error': False, 'content': '/~main-view'}]


def test_invalid_tool_input_is_answered_by_the_server(monkeypatch):
    broken = _tool_use('t3', 'model_get', model='Author')  # id missing, e.g. truncated while streaming
    client = FakeClient(script=[((), 'tool_use', [broken]), (('Sorry.',), 'end_turn', ())])
    with override_settings(**AI):
        _, received = run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Delete'}], client, monkeypatch)
    assert 'ai_actions' not in [m['type'] for m in received]
    assert received[-1]['type'] == 'ai_answer'
    result = client.calls[1]['messages'][-1]['content'][0]
    assert result['is_error'] and result['content'].startswith('INVALID_JSON')


def test_wrong_action_results_keep_history(monkeypatch):
    client = FakeClient(script=[((), 'tool_use', [LOAD]), (('Done.',), 'end_turn', ())])
    with override_settings(**AI):
        _, received = run(_user(), [
            {'event': 'prompt', 'id': 1, 'prompt': 'Load'},
            {'event': 'action_results', 'id': 1, 'results': [{'tool_use_id': 'nope', 'content': 'x'}]},
            {'event': 'action_results', 'id': 2, 'results': [{'tool_use_id': 't1', 'content': 'x'}]},
            {'event': 'action_results', 'id': 1, 'results': [{'tool_use_id': 't1', 'content': 'x'}]},
        ], client, monkeypatch)
    assert [m['type'] for m in received] == ['ai_actions', 'error', 'error', 'ai_delta', 'ai_answer']


def test_new_prompt_cancels_pending_actions(monkeypatch):
    client = FakeClient(script=[((), 'tool_use', [LOAD]), (('Ok.',), 'end_turn', ())])
    with override_settings(**AI):
        run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Load'},
                      {'event': 'prompt', 'id': 2, 'prompt': 'Never mind'}], client, monkeypatch)
    messages = client.calls[1]['messages']
    assert [m['role'] for m in messages] == ['user', 'assistant', 'user', 'user']
    assert messages[2]['content'][0]['tool_use_id'] == 't1' and messages[2]['content'][0]['is_error']
    assert messages[3]['content'] == 'Never mind'


def test_round_limit_forces_an_answer(monkeypatch):
    client = FakeClient(script=[((), 'tool_use', [LOAD])])  # the model would act forever
    events = [{'event': 'prompt', 'id': 1, 'prompt': 'Loop'}] + [
        {'event': 'action_results', 'id': 1, 'results': [{'tool_use_id': 't1', 'content': 'x'}]}] * 5
    with override_settings(**AI):
        run(_user(), events, client, monkeypatch)
    assert len(client.calls) == 6
    assert 'tool_choice' not in client.calls[4]
    assert client.calls[5]['tool_choice'] == {'type': 'none'}


# ------------------------------------------------------------------ OpenAI-compatible provider
def _chunk(content=None, tool_calls=None, finish_reason=None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=tool_calls),
                                                    finish_reason=finish_reason)])


def _call_part(index, id=None, name=None, arguments=None):
    return SimpleNamespace(index=index, id=id, function=SimpleNamespace(name=name, arguments=arguments))


class FakeOpenAIClient:
    """Streams ``script`` (one list of chunks per request; the last one repeats)."""

    def __init__(self, script):
        self.calls, self.script = [], script
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **params):
        self.calls.append(params | {'messages': list(params['messages'])})
        chunks = self.script[min(len(self.calls), len(self.script)) - 1]

        async def gen():
            for c in chunks:
                yield c
        return gen()


OPENAI = AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False, 'SDC_AI_PROVIDER': 'openai-compatible',
               'SDC_AI_MODEL': 'GPT-OSS:120b'}
OPENAI_TOKEN = {'event': 'set_config', 'token': 'sk-kit'}


def test_openai_tool_calls_and_results(monkeypatch):
    client = FakeOpenAIClient([
        [_chunk('Looking'), _chunk(' up.'),
         # The call arrives in pieces: id and name first, then the arguments in two parts
         _chunk(tool_calls=[_call_part(0, 'call_a', 'model_load', '{"model": ')]),
         _chunk(tool_calls=[_call_part(0, None, None, '"Author"}')]),
         _chunk(finish_reason='tool_calls')],
        [_chunk('There are 2.'), _chunk(finish_reason='stop')],
    ])
    with override_settings(**OPENAI):
        _, received = run(_user(), [OPENAI_TOKEN, {'event': 'prompt', 'id': 1, 'prompt': 'How many?'},
                                    {'event': 'action_results', 'id': 1,
                                     'results': [{'tool_use_id': 'call_a', 'content': [{'id': 1}, {'id': 2}]}]}],
                          client, monkeypatch)
    actions = next(m for m in received if m['type'] == 'ai_actions')
    assert actions['text'] == 'Looking up.'
    assert actions['actions'] == [{'tool_use_id': 'call_a', 'name': 'model_load', 'input': {'model': 'Author'}}]
    assert received[-1] == {'type': 'ai_answer', 'id': 1, 'text': 'Looking up.There are 2.',
                            'stop_reason': 'end_turn', 'is_error': False}
    first, second = client.calls
    assert first['model'] == 'GPT-OSS:120b' and first['stream'] is True
    assert first['messages'][0]['role'] == 'system' and 'simpledomcontrol' in first['messages'][0]['content']
    assert first['tools'][0] == {'type': 'function', 'function': {
        'name': 'navigate', 'description': AI_TOOLS[0]['description'], 'parameters': AI_TOOLS[0]['input_schema']}}
    assert second['messages'][2:] == [
        {'role': 'assistant', 'content': 'Looking up.', 'tool_calls': [
            {'id': 'call_a', 'type': 'function', 'function': {'name': 'model_load', 'arguments': '{"model": "Author"}'}}]},
        {'role': 'tool', 'tool_call_id': 'call_a', 'content': '[{"id": 1}, {"id": 2}]'}]


def test_openai_invalid_arguments_and_errors(monkeypatch):
    client = FakeOpenAIClient([
        [_chunk(tool_calls=[_call_part(0, 'call_b', 'navigate', '{"path": ')]), _chunk(finish_reason='tool_calls')],
        [_chunk('Sorry.'), _chunk(finish_reason='stop')],
    ])
    with override_settings(**OPENAI):
        _, received = run(_user(), [OPENAI_TOKEN, {'event': 'prompt', 'id': 1, 'prompt': 'Go'}], client, monkeypatch)
    assert 'ai_actions' not in [m['type'] for m in received]
    tool_message = client.calls[1]['messages'][-1]
    assert tool_message['role'] == 'tool' and tool_message['content'].startswith('Error: INVALID_JSON')


def test_provider_change_starts_new_conversation(monkeypatch):
    client = FakeClient()
    with override_settings(**AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False}):
        _, received = run(_user(), [{'event': 'set_config', 'token': 'sk'},
                                    {'event': 'prompt', 'id': 1, 'prompt': 'Hi'},
                                    {'event': 'set_config', 'provider': 'anthropic', 'model': 'claude-sonnet-5-5'},
                                    {'event': 'prompt', 'id': 2, 'prompt': 'Same provider'},
                                    {'event': 'set_config', 'provider': 'openai-compatible'},
                                    {'event': 'set_config', 'provider': 'anthropic'},
                                    {'event': 'prompt', 'id': 3, 'prompt': 'New'},
                                    {'event': 'set_config', 'provider': 'gemini'}],
                          client, monkeypatch, with_config=True)
    assert [m['role'] for m in client.calls[1]['messages']] == ['user', 'assistant', 'user']
    assert [m['role'] for m in client.calls[2]['messages']] == ['user']
    configs = [m for m in received if m['type'] == 'ai_config']
    assert configs[0]['providers'] == ['anthropic', 'openai-compatible']
    assert received[-1]['scope'] == 'settings' and 'Provider' in received[-1]['msg']


def _provider_error(status):
    error_class = type('APIStatusError', (Exception,), {'__module__': 'anthropic._exceptions'})
    error = error_class('provider error')
    error.status_code, error.message = status, "{'detail': 'Method Not Allowed'}"
    error.request = SimpleNamespace(method='POST', url='https://ki-toolbox.example.com/api/v1/v1/messages')
    return error


class FailingClient(FakeClient):
    def _stream(self, **params):
        raise _provider_error(405)


def test_provider_error_is_readable(monkeypatch):
    with override_settings(**AI | {'SDC_AI_TOKEN_FROM_SYSTEM': False}):
        _, received = run(_user(), [{'event': 'set_config', 'token': 'sk'},
                                    {'event': 'prompt', 'id': 1, 'prompt': 'Hi'}], FailingClient(), monkeypatch)
    assert received[-1]['scope'] == 'settings'
    assert '405' in received[-1]['msg'] and 'POST https://ki-toolbox.example.com' in received[-1]['msg']
    assert 'provider' in received[-1]['msg']


def test_provider_error_hides_system_url(monkeypatch):
    with override_settings(**AI):
        _, received = run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Hi'}], FailingClient(), monkeypatch)
    assert received[-1]['scope'] is None and '405' in received[-1]['msg']
    assert 'ki-toolbox' not in received[-1]['msg']


def test_additional_skill_files(tmp_path):
    (tmp_path / 'workflows.md').write_text('# Workflows\nLend a book via the borrow button.\n')
    (tmp_path / 'more.md').write_text('Opening hours: 9-17.')
    with override_settings(BASE_DIR=tmp_path, SDC_AI_ADDITIONAL_SKILL_FILE='workflows.md'):
        assert SDCAiConsumer._system_prompt().endswith('# Workflows\nLend a book via the borrow button.')
    # A list; absolute paths are kept, missing files are skipped
    with override_settings(BASE_DIR=tmp_path, SDC_AI_ADDITIONAL_SKILL_FILE=[str(tmp_path / 'more.md'), 'missing.md']):
        assert SDCAiConsumer._system_prompt().endswith('Opening hours: 9-17.')
    with override_settings(SDC_AI_ADDITIONAL_SKILL_FILE=None):
        assert SDCAiConsumer._additional_skills() == []


def test_assistant_view_without_setting():
    from django.conf import settings
    from django.test import RequestFactory
    from sdc_tools.sdc_views import SdcAiAssistant
    with override_settings():
        del settings.SDC_AI_ASSISTANT
        response = SdcAiAssistant().get_content(RequestFactory().get('/'))
    assert response.status_code == 200 and response.content == b''


def test_write_tools_are_rejected(monkeypatch):
    """Even if a model calls a tool that does not exist (any more), it never reaches the browser."""
    calls = [SimpleNamespace(type='tool_use', id='t1', name='model_delete', input={'model': 'Author', 'id': 1}),
             _tool_use('t2', 'fill_form', form='0', values={'name': 'x'}),  # form must be an integer
             _tool_use('t3', 'fill_form', form=0, values={'name': 'Jane'})]
    client = FakeClient(script=[((), 'tool_use', calls), (('Done.',), 'end_turn', ())])
    with override_settings(**AI):
        _, received = run(_user(), [{'event': 'prompt', 'id': 1, 'prompt': 'Delete'},
                                    {'event': 'action_results', 'id': 1,
                                     'results': [{'tool_use_id': 't3', 'content': {'set': {'name': 'Jane'}}}]}],
                          client, monkeypatch)
    actions = next(m for m in received if m['type'] == 'ai_actions')['actions']
    assert [a['tool_use_id'] for a in actions] == ['t3']
    results = client.calls[1]['messages'][-1]['content']
    assert results[0]['is_error'] and results[0]['content'] == 'Unknown tool model_delete'
    assert results[1]['is_error'] and 'wrong type' in results[1]['content']
    assert not results[2]['is_error']
