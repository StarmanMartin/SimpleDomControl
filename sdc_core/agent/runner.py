"""
Runs the tests and the asset build of a project for ``manage.py sdc_agent test|build`` and returns a short summary;
the full output goes to ``.sdc_agent/logs/<name>.log``.
"""
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

MAX_FAILURES = 8
MAX_DETAIL_LINES = 6


@dataclass
class RunResult:
    name: str
    command: list
    returncode: int
    log: str
    summary: str = ''
    failures: list = field(default_factory=list)
    skipped: bool = False

    @property
    def ok(self):
        return self.returncode == 0


def package_manager(root):
    """``yarn`` if the project uses it (yarn.lock or packageManager), else ``npm``."""
    if os.path.exists(os.path.join(root, 'yarn.lock')):
        return 'yarn'
    try:
        import json
        with open(os.path.join(root, 'package.json'), encoding='utf-8') as f:
            if str(json.load(f).get('packageManager', '')).startswith('yarn'):
                return 'yarn'
    except (OSError, ValueError):
        pass
    return 'npm'


def script_command(root, script):
    return ['yarn', script] if package_manager(root) == 'yarn' else ['npm', 'run', script]


def run(name, command, root, timeout=1800):
    """Runs ``command`` in ``root`` and writes its output to the log file."""
    log_dir = os.path.join(root, '.sdc_agent', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log = os.path.join(log_dir, f'{name}.log')
    env = dict(os.environ, FORCE_COLOR='0', NO_COLOR='1', CI='1')
    try:
        result = subprocess.run(command, cwd=root, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, timeout=timeout)
        output, code = result.stdout + result.stderr, result.returncode
    except FileNotFoundError as e:
        output, code = f'{e}\n', 127
    except subprocess.TimeoutExpired as e:
        output, code = f'{e.stdout or ""}{e.stderr or ""}\nTimeout after {timeout} s\n', 124
    with open(log, 'w', encoding='utf-8') as f:
        f.write(output)
    return RunResult(name, command, code, log), output


def _blocks(lines, start_re, stop_re):
    """Blocks of lines starting at ``start_re`` up to (not including) a ``stop_re`` line."""
    blocks, current = [], None
    for line in lines:
        if start_re.match(line):
            if current:
                blocks.append(current)
            current = [line]
        elif current is not None:
            if stop_re.match(line):
                blocks.append(current)
                current = None
            else:
                current.append(line)
    if current:
        blocks.append(current)
    return blocks


def summarize_django(result, output):
    """``manage.py test``: 'Ran N tests', OK/FAILED and per failure its name and the exception line."""
    lines = output.splitlines()
    ran = next((l for l in reversed(lines) if l.startswith('Ran ')), '')
    status = next((l for l in reversed(lines) if l.startswith(('OK', 'FAILED'))), '')
    result.summary = ' '.join(part for part in (ran, status) if part) or (lines[-1] if lines else 'no output')
    # A block runs from 'FAIL: …' / 'ERROR: …' to the next '=====' line (the '-----' line below the title is part
    # of it)
    for block in _blocks(lines, re.compile(r'^(FAIL|ERROR): '), re.compile(r'^=+$|^Ran ')):
        exception = next((l for l in reversed(block) if re.match(r'^\w[\w.]*(Error|Exception|Failure)\b', l)),
                         block[-1] if len(block) > 1 else '')
        result.failures.append(f'{block[0]}\n    {exception.strip()}')
    return result


def summarize_jest(result, output):
    """Jest: the 'Tests:' summary line and per failing test its title and the first lines of the error."""
    lines = output.splitlines()
    result.summary = ' | '.join(l.strip() for l in lines if re.match(r'^\s*(Test Suites|Tests):', l)) or \
        (lines[-1] if lines else 'no output')
    for block in _blocks(lines, re.compile(r'^\s+● (?!Console)'), re.compile(r'^\s+● |^(Test Suites|Tests):')):
        detail = [l.strip() for l in block[1:] if l.strip() and not l.strip().startswith('at ')][:MAX_DETAIL_LINES]
        result.failures.append(block[0].strip() + ''.join(f'\n    {d}' for d in detail))
    return result


def summarize_build(result, output):
    """Asset build (gulp/webpack): 'compiled successfully' or the ERROR blocks."""
    lines = output.splitlines()
    errors = [i for i, l in enumerate(lines) if re.search(r'\bERROR\b|Error:', l)]
    for i in errors[:MAX_FAILURES]:
        result.failures.append('\n    '.join(l.strip() for l in lines[i:i + MAX_DETAIL_LINES] if l.strip()))
    compiled = next((l.strip() for l in reversed(lines) if 'compiled' in l), '')
    result.summary = compiled or ('build ok' if result.ok else f'build failed (exit {result.returncode})')
    return result


def run_python_tests(root, args=()):
    result, output = run('test-python', [sys.executable, 'manage.py', 'test', *args], root)
    return summarize_django(result, output)


def missing_node_modules(root, name):
    """A not-run result when the npm packages are not installed (Jest and the asset build need them)."""
    if os.path.isdir(os.path.join(root, 'node_modules')):
        return None
    install = 'yarn install' if package_manager(root) == 'yarn' else 'npm install'
    result = RunResult(name, [], 2, '-', summary=f'not run: no node_modules (install the npm packages first: '
                                                    f'`{install}`). Without them rely on `sdc_agent check` and the '
                                                    f'Django tests.')
    result.skipped = True
    return result


def run_js_tests(root, args=()):
    skipped = missing_node_modules(root, 'test-js')
    if skipped:
        return skipped
    result, output = run('test-js', script_command(root, 'sdc_test') + list(args), root)
    return summarize_jest(result, output)


def run_build(root, mode='build'):
    skipped = missing_node_modules(root, 'build')
    if skipped:
        return skipped
    result, output = run('build', script_command(root, mode), root)
    return summarize_build(result, output)
