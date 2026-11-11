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


def run_claude(project, prompt, model, budget_usd, timeout_s=1800, extra_args=(), permissions='restricted'):
    """
    Runs ``claude -p`` in ``project`` and returns a dict with turns, tokens, cost, duration and the final message.
    User settings, hooks and MCP servers are not loaded. ``permissions``: ``restricted`` (default: file tools and
    the commands in ``RESTRICTED_TOOLS``) or ``bypass`` (no permission checks; only in a container or VM).
    """
    command = ['claude', '-p', prompt, '--output-format', 'json', *permission_args(permissions),
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
    try:
        data = json.loads(result.stdout)
    except ValueError:
        return {'error': f'no JSON output (exit {result.returncode})', 'stderr': result.stderr[-2000:],
                'stdout': result.stdout[-2000:], 'wall_s': wall}
    usage = data.get('usage') or {}
    return {
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
