"""Helpers of ``manage.py sdc_eval_ai --agent mcp``: an AI model that uses the MCP endpoint (``sdc_mcp/``) of the app.

The episode runs in the evaluation command, without a browser: the command connects to the throwaway server with an
API token of the task's user, takes the server instructions as system prompt and the server's tools as the model's
tools, and lets the model call them until it answers. The model providers are those of the AI assistant
(``SDCAiConsumer``): the HTTP requests to the model are made by its code, not by a second client.

Everything here works on plain data or on an object with the interface of ``McpTransport``, so that it can be tested
without a server (see ``pytests/test_eval_ai_mcp.py``).

MCP tasks use the task format of ``eval_ai`` with these additions::

    agent: mcp                  # optional: the agent that runs the task (the other one skips it)
    privileges: [model:*:read]  # privileges of the API token (privileges or presets); default: --mcp-privileges
    expect:
      records:                  # records of the database after the episode (plain ORM filters)
        - model: Sample         # "app_label.Model" or "Model"
          filter: {name: "NMR 400"}
          count: 1              # n, or {min: 1, max: 3}; default: at least one
          fields: {room: "3.12"}    # values of the first matching record
      tools_used: [model_load, [sample_create, sample_update]]   # a nested list = any of its alternatives
      tools_not_used: [sample_delete]
      max_tool_errors: 0        # tool calls that returned an error
    reference:                  # one step per model response, replayed by --model oracle
      - model_load: {model: Sample}
      - answer: There are three samples.
"""
import asyncio
import datetime
import decimal
import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict

# Tool results are recorded (and checked for forbidden values) up to this length
MAX_RESULT_CHARS = 20000
DECLINED_TEXT = 'The user declined this action.'
PROTOCOL_VERSION = '2025-06-18'
MCP_CONDITIONS = ('full', 'none')
DEFAULT_SYSTEM_PROMPT = 'You are an assistant that uses the tools of a website to fulfil the requests of the user.'

# Tools of the harness: model APIs have no native MCP resources
HARNESS_TOOLS = [
    {'name': 'resources_list', 'description': 'List the documentation resources of the website (MCP resources/list): '
                                              'uri, title and description of each.',
     'input_schema': {'type': 'object', 'properties': {}}},
    {'name': 'resources_read', 'description': 'Read a documentation resource of the website by its uri '
                                              '(MCP resources/read).',
     'input_schema': {'type': 'object', 'required': ['uri'], 'additionalProperties': False,
                      'properties': {'uri': {'type': 'string', 'description': 'The uri from resources_list'}}}},
]


class McpError(Exception):
    """A JSON-RPC error of the server (its message is shown to the model)."""


class TransportError(Exception):
    """The request failed (HTTP status, connection); ``status`` is the HTTP status or None."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class AgentError(Exception):
    """The agent loop cannot continue (e.g. the model declined or its answer was cut off)."""


# ---------------------------------------------------------------------------------------- tasks, conditions
def parse_privileges(spec):
    """``--mcp-privileges``: comma-separated privileges or presets (``read``, ``model:*:read,account:read``)."""
    return [p.strip() for p in (spec or '').split(',') if p.strip()]


def parse_mcp_condition(spec):
    """
    ``[label=]full|none`` -> ``{'label', 'spec', 'settings': {}, 'mcp': {...}}``. ``full``: the instructions with
    the app's ``instructions_extra`` and resources; ``none``: without them (sdc's base text and the model index only).
    """
    from sdc_core.management.commands.utils.eval_ai import EvalConfigError
    label, _, source = spec.rpartition('=')
    if source not in MCP_CONDITIONS:
        raise EvalConfigError(f'Condition {spec!r}: with --agent mcp the source must be one of '
                              f'{", ".join(MCP_CONDITIONS)}')
    override = {'enabled': True} | ({'instructions_extra': None, 'resources': []} if source == 'none' else {})
    return {'label': label or source, 'spec': spec, 'settings': {}, 'mcp': override}


def mcp_settings_source(base_module, condition):
    """Source of a settings module that imports the project's settings and overrides ``SDC_MCP`` for a condition."""
    return (f'from {base_module} import *  # noqa: F401,F403\n\n'
            f"SDC_MCP = dict(globals().get('SDC_MCP') or {{}}, **{condition['mcp']!r})\n")


def parse_mcp_model(spec):
    """``oracle`` (replays the references of the tasks) or a model spec like ``--model`` of the browser mode."""
    from sdc_core.management.commands.utils.eval_ai import parse_model
    if spec == 'oracle':
        return {'label': 'oracle', 'spec': 'oracle', 'settings': {'SDC_AI_PROVIDER': 'oracle', 'SDC_AI_MODEL': 'oracle',
                                                                  'SDC_AI_BASE_URL': ''}}
    return parse_model(spec)


# ------------------------------------------------------------------------------------------- tool conversion
def mcp_tool_schema(tool):
    """An MCP tool definition (``tools/list``) as a model tool ``{'name', 'description', 'input_schema'}``."""
    description = (tool.get('description') or tool.get('title') or tool['name']).strip()
    return {'name': tool['name'], 'description': description,
            'input_schema': tool.get('inputSchema') or {'type': 'object', 'properties': {}}}


def model_tools(mcp_tools):
    """The tools offered to the model: those of the server plus the harness tools for resources."""
    return [mcp_tool_schema(t) for t in mcp_tools] + [dict(t) for t in HARNESS_TOOLS]


def needs_confirmation(tool):
    """True for a tool that may change data (annotation ``readOnlyHint`` missing or false): the user is asked."""
    return tool is not None and not (tool.get('annotations') or {}).get('readOnlyHint', False)


def result_text(result):
    """The text of an MCP result (``content`` blocks; ``structuredContent`` if there are none)."""
    parts = []
    for block in result.get('content') or []:
        if isinstance(block, dict) and block.get('type') == 'text':
            parts.append(str(block.get('text', '')))
        else:
            parts.append(json.dumps(block, ensure_ascii=False, default=str))
    if not parts and result.get('structuredContent') is not None:
        parts.append(json.dumps(result['structuredContent'], ensure_ascii=False, default=str))
    return '\n'.join(parts)


def resource_text(result):
    """The text of a ``resources/read`` result (blobs are named, not included)."""
    parts = []
    for content in result.get('contents') or []:
        parts.append(content['text'] if 'text' in content else f'[binary content of {content.get("uri")}]')
    return '\n'.join(parts)


def scrub(text, secrets):
    """``text`` without the secrets (a token must never reach a result file, a log or an error message)."""
    for secret in filter(None, secrets):
        text = text.replace(secret, '***')
    return text


# --------------------------------------------------------------------------------------------- transport
class HttpTransport:
    """JSON-RPC over HTTP (Streamable HTTP, one POST per message) with an API token."""

    def __init__(self, base_url, secret, url_path='/sdc_mcp/', timeout=120):
        self.url = base_url.rstrip('/') + url_path
        self.secret = secret
        self.timeout = timeout
        self.version = None
        self.counter = 0

    def _post(self, message):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'Authorization': f'Bearer {self.secret}'}
        if self.version:
            headers['MCP-Protocol-Version'] = self.version
        request = urllib.request.Request(self.url, json.dumps(message).encode(), headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as e:
            raise TransportError(f'HTTP {e.code} from {self.url}', e.code)
        except (urllib.error.URLError, OSError) as e:
            raise TransportError(f'Cannot reach {self.url}: {getattr(e, "reason", e)}')

    def call(self, method, params=None):
        """The ``result`` of a request; ``McpError`` for a JSON-RPC error, ``TransportError`` for HTTP problems."""
        self.counter += 1
        message = {'jsonrpc': '2.0', 'id': self.counter, 'method': method}
        if params is not None:
            message['params'] = params
        _, body = self._post(message)
        data = json.loads(body)
        if 'error' in data:
            raise McpError(data['error'].get('message', 'error'))
        return data.get('result') or {}

    def notify(self, method):
        self._post({'jsonrpc': '2.0', 'method': method})


def connect(transport):
    """Initializes the connection; returns ``(instructions, mcp tools)``."""
    info = transport.call('initialize', {'protocolVersion': PROTOCOL_VERSION, 'capabilities': {},
                                         'clientInfo': {'name': 'sdc_eval_ai', 'version': '1'}})
    transport.version = info.get('protocolVersion')
    transport.notify('notifications/initialized')
    tools = transport.call('tools/list').get('tools') or []
    return info.get('instructions') or DEFAULT_SYSTEM_PROMPT, tools


# ------------------------------------------------------------------------------------------------- runner
class ToolRunner:
    """
    Runs the tool calls of the model against the server and records them. ``confirm``: the answer of the simulated
    user before a tool that may change data (``allow`` / ``deny``).
    """

    def __init__(self, transport, mcp_tools, confirm='deny', secrets=()):
        self.transport = transport
        self.tools = {t['name']: t for t in mcp_tools}
        self.confirm = confirm
        self.secrets = list(secrets)
        self.calls, self.confirmations, self.tool_results, self.http_errors = [], [], [], []

    def run(self, name, arguments):
        """Runs one tool call; returns ``(text, is_error)`` for the model and records the call."""
        valid = isinstance(arguments, dict)
        call = {'name': name, 'arguments': arguments if valid else None, 'is_error': False}
        self.calls.append(call)
        if not valid:
            text, is_error = 'The arguments are not a valid JSON object.', True
            call['invalid'] = True
        elif self._declined(name, arguments):
            call['declined'] = True
            text, is_error = DECLINED_TEXT, False
        else:
            text, is_error = self._dispatch(name, arguments)
        text = scrub(text, self.secrets)
        call['is_error'] = is_error
        self.tool_results.append(text[:MAX_RESULT_CHARS])
        return text, is_error

    def _declined(self, name, arguments):
        if not needs_confirmation(self.tools.get(name)):
            return False
        self.confirmations.append(f'Run {name} with {json.dumps(arguments, ensure_ascii=False, sort_keys=True)}?')
        return self.confirm != 'allow'

    def _dispatch(self, name, arguments):
        try:
            if name == 'resources_list':
                return json.dumps(self.transport.call('resources/list'), ensure_ascii=False), False
            if name == 'resources_read':
                return resource_text(self.transport.call('resources/read', {'uri': arguments.get('uri')})), False
            result = self.transport.call('tools/call', {'name': name, 'arguments': arguments})
            return result_text(result), bool(result.get('isError'))
        except McpError as e:
            return str(e), True
        except TransportError as e:
            if e.status is not None:
                self.http_errors.append({'url': '/sdc_mcp/', 'status': e.status})
            return str(e), True


# -------------------------------------------------------------------------------------------- model sessions
def consumer_session(model_values, system_prompt, tools):
    """
    A model session on the provider code of the AI assistant (``SDCAiConsumer``: Anthropic and OpenAI-compatible
    streaming, message formats and tool results). Keys come from ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``.
    ``model_values``: ``{'provider', 'model', 'base_url', 'effort', 'max_tokens'}``.
    """
    from sdc_core.consumers import SDCAiConsumer

    class EvalProvider(SDCAiConsumer):
        """The consumer without a WebSocket: only its model requests are used."""

        def _config(self, key):
            return model_values.get(key) or {'effort': '', 'base_url': '', 'max_tokens': 16000}.get(key)

        def _uses_system_token(self):
            return True

        def _tools(self):
            return tools

        async def _send_delta(self, id, text):
            pass

        async def _count_request(self):
            return True

        def _metrics_enabled(self):
            return False

    return ConsumerSession(EvalProvider(), system_prompt)


class ConsumerSession:
    """A conversation with a model through the provider code of ``SDCAiConsumer``."""

    def __init__(self, provider, system_prompt):
        self.provider = provider
        provider.messages = []
        provider.config = {}
        provider.client = None
        provider.system_prompt = system_prompt

    def add_user(self, text):
        self.provider.messages.append({'role': 'user', 'content': text})

    async def step(self, final=False):
        """One model response: ``{'text', 'tool_uses': [{'id', 'name', 'input'}], 'stop', 'usage'}``."""
        result = await self.provider._stream(0, final=final)
        if result['stop'] == 'refusal':
            raise AgentError('The model declined to answer the request')
        if result['tool_uses'] and result['stop'] != 'tool_use':
            raise AgentError('The answer was cut off (raise --max-tokens)')
        self.provider.messages.append(result['message'])
        return {k: result[k] for k in ('text', 'tool_uses', 'stop', 'usage')}

    def add_tool_results(self, results):
        """``results``: ``[(tool_use_id, text, is_error)]``, one per tool use of the last step."""
        self.provider.pending = {'tool_use_ids': [r[0] for r in results],
                                 'results': {r[0]: {'content': r[1], 'is_error': r[2]} for r in results}}
        self.provider._append_tool_results()


class OracleSession:
    """
    Replays the ``reference`` of a task as the model's responses: a step ``{tool: arguments}`` is a tool call,
    ``{answer: text}`` the answer; after the last step it answers "Done.". Validates a task without a model.
    """

    def __init__(self, reference):
        self.reference = list(reference or [])
        self.index = 0

    def add_user(self, text):
        pass

    async def step(self, final=False):
        step = self.reference[self.index] if self.index < len(self.reference) else {'answer': 'Done.'}
        name, value = next(iter(step.items()))
        self.index += 1
        if name == 'answer':
            return {'text': str(value), 'tool_uses': [], 'stop': 'end_turn', 'usage': None}
        return {'text': '', 'stop': 'tool_use', 'usage': None,
                'tool_uses': [{'id': f'oracle_{self.index}', 'name': name, 'input': value or {}}]}

    def add_tool_results(self, results):
        pass


# ----------------------------------------------------------------------------------------------- the loop
def run_agent(session, runner, prompts, max_turns, timeout):
    """
    Lets the model work on the prompts (the first one and the follow-ups) until it answers each; a turn is one
    model request. The requests run on one event loop (the provider's HTTP client keeps its connections); the tool
    calls run between them, outside of it. ``timeout``: seconds for the whole episode.
    Returns ``{'answers', 'turns', 'requests', 'transcript', 'max_turns_reached'}``.
    """
    episode = {'answers': [], 'turns': 0, 'requests': [], 'transcript': [], 'max_turns_reached': False}
    deadline = time.monotonic() + timeout
    loop = asyncio.new_event_loop()
    try:
        for prompt in prompts:
            session.add_user(prompt)
            episode['transcript'].append({'user': prompt})
            texts = []
            while episode['turns'] < max_turns:
                started = time.monotonic()
                if started >= deadline:
                    raise TimeoutError(f'No answer within {timeout}s')
                result = loop.run_until_complete(asyncio.wait_for(session.step(), deadline - started))
                episode['turns'] += 1
                episode['requests'].append({'usage': result.get('usage') or {}, 'tool_calls': len(result['tool_uses']),
                                            'duration_ms': round((time.monotonic() - started) * 1000)})
                if result['text']:
                    texts.append(result['text'])
                    episode['transcript'].append({'assistant': result['text'][:2000]})
                if not result['tool_uses']:
                    break
                outputs = []
                for use in result['tool_uses']:
                    text, is_error = runner.run(use['name'], use['input'])
                    outputs.append((use['id'], text, is_error))
                    episode['transcript'].append({'tool': use['name'], 'input': use['input'], 'is_error': is_error,
                                                  'result': text[:500]})
                session.add_tool_results(outputs)
            else:
                episode['max_turns_reached'] = True
            episode['answers'].append('\n'.join(texts))
            if episode['max_turns_reached']:
                break
    finally:
        loop.close()
    return episode


def run_episode(session, transport, secret, prompts, ops):
    """
    The whole agent episode with ``session`` as the model: connects (``connect``), runs the loop with the tools of the
    server and the harness. Returns the episode dict for ``check_episode`` (``error`` instead of raising).
    ``session``: a callable ``(instructions, tools) -> model session`` (``consumer_session`` or ``OracleSession``).
    """
    runner = None
    try:
        instructions, mcp_tools = connect(transport)
        runner = ToolRunner(transport, mcp_tools, ops.get('confirm') or 'deny', [secret])
        model = session(instructions, model_tools(mcp_tools))
        episode = run_agent(model, runner, prompts, ops['max_turns'], ops['episode_timeout'] * len(prompts))
        episode['system_prompt'] = instructions
        episode['answer'] = episode['answers'][-1] if episode['answers'] else ''
    except Exception as e:  # noqa: BLE001 - one failing episode must not stop the evaluation
        message = f'{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ""}'
        episode = {'error': scrub(message, [secret]), 'answers': [], 'turns': 0, 'requests': [], 'transcript': [],
                   'max_turns_reached': False}
    if runner is not None:
        episode |= {'tool_calls': runner.calls, 'confirmations': runner.confirmations,
                    'tool_results': runner.tool_results, 'http_errors': runner.http_errors}
    return episode


def mcp_metrics(episode):
    """Effort and grounding metrics of an MCP episode, with the names of ``episode_metrics`` (browser mode)."""
    calls = episode.get('tool_calls') or []
    requests = episode.get('requests') or []
    usage = defaultdict(int)
    for r in requests:
        for k, v in (r.get('usage') or {}).items():
            usage[k] += v
    by_name = defaultdict(int)
    for c in calls:
        by_name[c['name']] += 1
    prompt = episode.get('system_prompt') or ''
    lengths = [len(t) for t in episode.get('tool_results') or []]
    return {
        'model_requests': len(requests), 'turns': episode.get('turns', 0),
        'action_rounds': sum(1 for r in requests if r['tool_calls']), 'tool_calls': len(calls),
        'tool_calls_by_name': dict(by_name), 'invalid_tool_inputs': sum(1 for c in calls if c.get('invalid')),
        'tool_errors': sum(1 for c in calls if c['is_error']), 'request_errors': 0, 'usage': dict(usage),
        'model_ms': sum(r['duration_ms'] for r in requests),
        'system_prompt_sha256': [hashlib.sha256(prompt.encode()).hexdigest()] if prompt else [],
        'system_prompt_chars': len(prompt), 'tool_result_chars': sum(lengths),
        'max_tool_result_chars': max(lengths, default=0),
    }


# ------------------------------------------------------------------------------------------------ records
def _plain(value):
    """A value of a record as JSON data (relations as primary keys)."""
    if hasattr(value, 'pk') and hasattr(value, '_meta'):
        return _plain(value.pk)
    if hasattr(value, 'all') and hasattr(value, 'model'):
        return sorted((_plain(v) for v in value.all()), key=str)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID)):
        return str(value)
    return str(value)


def _resolve_model(name):
    from django.apps import apps
    if '.' in name:
        return apps.get_model(name)
    matches = [m for m in apps.get_models() if m.__name__ == name]
    if len(matches) != 1:
        raise LookupError(f'{len(matches)} models are named {name}' if matches else f'unknown model {name}')
    return matches[0]


def evaluate_records(specs):
    """
    Evaluates the ``records`` checks in the current database with plain ORM filters (the harness is trusted).
    Returns one ``{'model', 'filter', 'count', 'fields': {name: value} of the first match | None}`` per spec, or
    ``{'model', 'filter', 'error'}`` if the spec cannot be evaluated.
    """
    results = []
    for spec in specs:
        entry = {'model': spec['model'], 'filter': spec.get('filter') or {}}
        try:
            queryset = _resolve_model(spec['model'])._base_manager.filter(**entry['filter']).order_by('pk')
            first = queryset.first()
            entry |= {'count': queryset.count(),
                      'fields': {name: _plain(getattr(first, name)) for name in spec.get('fields') or {}
                                 } if first is not None else None}
        except Exception as e:  # noqa: BLE001 - a wrong spec is reported in the result, not raised
            entry['error'] = f'{type(e).__name__}: {e}'
        results.append(entry)
    return results


def record_matches(spec, result):
    """True if the ``records`` spec is met by its ``evaluate_records`` result."""
    from sdc_core.management.commands.utils.eval_ai import _same
    if result.get('error'):
        return False
    count, wanted = result['count'], spec.get('count')
    if isinstance(wanted, dict):
        low, high = wanted.get('min', 0), wanted.get('max')
    elif wanted is not None:
        low = high = wanted
    else:
        low, high = 1, None
    if count < low or (high is not None and count > high):
        return False
    fields = result.get('fields') or {}
    wanted_fields = (spec.get('fields') or {}).items()
    return all(name in fields and _same(expected, fields[name]) for name, expected in wanted_fields)
