"""Runs Claude Code headless in a benchmark project and returns its usage (see agents.architecture.md, 3)."""
import json
import subprocess
import time

from project import env_for


# Tools of the "restricted" mode: file tools (edits only inside the project, acceptEdits) and a few shell commands.
# Anything else is denied without a prompt (-p mode), and the agent has to do without it.
RESTRICTED_TOOLS = ['Read', 'Edit', 'Write', 'Glob', 'Grep',
                    'Bash(python:*)', 'Bash(python3:*)', 'Bash(ls:*)', 'Bash(cat:*)', 'Bash(head:*)',
                    'Bash(git status:*)', 'Bash(git diff:*)']


def permission_args(mode):
    if mode == 'restricted':
        return ['--permission-mode', 'acceptEdits', '--allowedTools', ','.join(RESTRICTED_TOOLS)]
    if mode == 'bypass':
        return ['--permission-mode', 'bypassPermissions']
    raise ValueError(f'Unknown permission mode {mode}')


def run_claude(project, prompt, model, budget_usd, timeout_s=1800, extra_args=(), permissions='restricted',
               transcript=False):
    """
    Runs ``claude -p`` in ``project`` and returns a dict with turns, tokens, cost, duration and the final message.
    User settings, hooks and MCP servers are not loaded. ``permissions``: ``restricted`` (default: file tools and
    the commands in ``RESTRICTED_TOOLS``) or ``bypass`` (no permission checks; only in a container or VM).
    ``transcript``: also return ``steps`` (see ``parse_stream``), using the stream-json output.
    """
    output_format = ['--output-format', 'stream-json', '--verbose'] if transcript else ['--output-format', 'json']
    command = ['claude', '-p', prompt, *output_format, *permission_args(permissions),
               '--setting-sources', 'project,local',
               '--strict-mcp-config', '--no-session-persistence',
               '--max-budget-usd', str(budget_usd)]
    if model:
        command += ['--model', model]
    command += list(extra_args)
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=project, env=env_for(project), stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {'error': f'timeout after {timeout_s} s', 'wall_s': round(time.monotonic() - started, 1)}
    wall = round(time.monotonic() - started, 1)
    steps = None
    try:
        if transcript:
            data, steps = parse_stream(result.stdout)
        else:
            data = json.loads(result.stdout)
    except ValueError:
        return {'error': f'no JSON output (exit {result.returncode})', 'stderr': result.stderr[-2000:],
                'stdout': result.stdout[-2000:], 'wall_s': wall}
    usage = data.get('usage') or {}
    extra = {'steps': steps} if steps is not None else {}
    return {**extra,
        'is_error': data.get('is_error'),
        'subtype': data.get('subtype'),
        'turns': data.get('num_turns'),
        'cost_usd': data.get('total_cost_usd'),
        'duration_ms': data.get('duration_ms'),
        'wall_s': wall,
        'input_tokens': usage.get('input_tokens'),
        'cache_creation_input_tokens': usage.get('cache_creation_input_tokens'),
        'cache_read_input_tokens': usage.get('cache_read_input_tokens'),
        'output_tokens': usage.get('output_tokens'),
        'model_usage': data.get('modelUsage'),
        'final_message': (data.get('result') or '')[-1500:],
    }


def total_input(agent):
    """All input tokens of a run (uncached, cache writes and cache reads)."""
    return sum(agent.get(key) or 0 for key in
               ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))


def _short(value, limit=300):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + '…'


def _result_size(content):
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(item.get('text', '')) for item in content if isinstance(item, dict))
    return 0


def parse_stream(stdout):
    """
    The final result object and a compact list of steps from ``claude -p --output-format stream-json --verbose``:
    ``{'turn', 'context', 'tool', 'input'}`` per tool call (``context``: input tokens of that model request,
    ``input``: the tool input shortened), ``{'result_chars', 'error'}`` added from the tool result, and
    ``{'turn', 'context', 'text_chars'}`` for answers without tools. File contents are not stored.
    """
    result, steps, by_id, turn, last_message = None, [], {}, 0, object()
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        event = json.loads(line)
        kind = event.get('type')
        if kind == 'result':
            result = event
        elif kind == 'assistant':
            message = event.get('message') or {}
            usage = message.get('usage') or {}
            context = sum(usage.get(k) or 0 for k in
                          ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
            # One model response may arrive as several events (one per content block) with the same id
            if message.get('id') is None or message.get('id') != last_message:
                turn += 1
            last_message = message.get('id')
            content = message.get('content') or []
            tools = [c for c in content if isinstance(c, dict) and c.get('type') == 'tool_use']
            for call in tools:
                step = {'turn': turn, 'context': context, 'tool': call.get('name'),
                        'input': _short(call.get('input'))}
                steps.append(step)
                by_id[call.get('id')] = step
            if not tools:
                text = sum(len(c.get('text', '')) for c in content if isinstance(c, dict))
                steps.append({'turn': turn, 'context': context, 'text_chars': text})
        elif kind == 'user':
            for item in (event.get('message') or {}).get('content') or []:
                if isinstance(item, dict) and item.get('type') == 'tool_result' and item.get('tool_use_id') in by_id:
                    step = by_id[item['tool_use_id']]
                    step['result_chars'] = _result_size(item.get('content'))
                    if item.get('is_error'):
                        step['error'] = True
    if result is None:
        raise ValueError('no result event in the stream')
    return result, steps


def summarize_steps(steps):
    """Counts per tool, files read, skills read and shell commands of one run."""
    tools, files, skills, commands = {}, [], [], []
    for step in steps or []:
        tool = step.get('tool')
        if not tool:
            continue
        tools[tool] = tools.get(tool, 0) + 1
        try:
            data = json.loads(step['input']) if step['input'].startswith('{') else {}
        except ValueError:
            data = {}
        path = data.get('file_path') or data.get('path') or ''
        if tool == 'Read' and path:
            files.append(path)
            if '/.claude/skills/' in path or path.startswith('.claude/skills/'):
                skills.append(path.split('.claude/skills/', 1)[1])
        elif tool == 'Skill':
            skills.append(data.get('skill') or data.get('name') or step['input'])
        elif tool == 'Bash':
            commands.append(data.get('command') or step['input'])
    return {'tools': tools, 'files_read': files, 'skills_read': skills, 'bash': commands}
