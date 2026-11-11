"""
Tests of the agent-friendly commands (projects/agents.plan.md, M1): no prompts outside a terminal, no rewritten
env files, and ``manage.py sdc_agent``. The commands run in a generated project like the other generation tests.
"""
import os
import shutil
import subprocess
import sys
import uuid

import pytest

from sdc_core.agent import runner
from sdc_core.apps import update_sdc_env_files

APP = 'test_app_one'


def _manage(project, *args):
    return subprocess.run([sys.executable, 'manage.py', *args], cwd=project, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True)


@pytest.fixture(scope='module')
def project():
    path = os.path.join(os.getcwd(), 'pytests', f'agent-{uuid.uuid4()}')
    try:
        shutil.copytree('./pytests/test_django_project(DUMMY)', path)
        assert _manage(path, 'sdc_init').returncode == 0
        assert _manage(path, 'sdc_cc', '-a', APP, '-c', 'shelf_view', '-m').returncode == 0
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _js(project, name):
    return os.path.join(project, APP, 'Assets', 'src', APP, 'controller', name, f'{name}.js')


def _organizer(project):
    return os.path.join(project, APP, 'Assets', 'src', APP, f'{APP}.organizer.js')


# ------------------------------------------------------------------ WP1.0: env files

def test_env_files_are_written_once(tmp_path):
    python = sys.executable
    assert len(update_sdc_env_files(str(tmp_path), python)) == 2
    env = (tmp_path / '.sdc_env').read_text()
    assert 'JSON_DATA_DUMP=' in env and 'COPY_DEFAULT_DB=' in env
    assert update_sdc_env_files(str(tmp_path), python) == []
    # A second interpreter path (e.g. python3 instead of python) does not rewrite the file while the first exists
    assert update_sdc_env_files(str(tmp_path), '/usr/bin/python3') == []


def test_env_files_keep_comments_and_values(tmp_path):
    (tmp_path / '.sdc_env').write_text('# my settings\nCOPY_DEFAULT_DB=0\n')
    (tmp_path / '.sdc_python_env').write_text('PYTHON="/does/not/exist"')
    written = update_sdc_env_files(str(tmp_path), sys.executable)
    env = (tmp_path / '.sdc_env').read_text()
    assert env.startswith('# my settings\nCOPY_DEFAULT_DB=0\n') and 'DB_PYTHON_SCRIPT=' in env
    assert len(written) == 2 and sys.executable in (tmp_path / '.sdc_python_env').read_text()


def test_manage_py_does_not_change_the_env_files(project):
    assets = os.path.join(project, 'Assets')
    before = {name: os.stat(os.path.join(assets, name)).st_mtime_ns for name in ('.sdc_env', '.sdc_python_env')}
    assert _manage(project, 'check').returncode == 0
    after = {name: os.stat(os.path.join(assets, name)).st_mtime_ns for name in before}
    assert before == after


# ------------------------------------------------------------------ WP1.1: no prompts

@pytest.mark.parametrize('args, flag', [
    (['sdc_cc', '-a', APP, '-m'], '-c/--controller_name'),
    (['sdc_cc', '-c', 'x_view', '-m'], '-a/--app_name'),
    (['sdc_new_model', '-a', APP], '-m/--model_name'),
    (['sdc_new_model', '-m', 'Shelf'], '-a/--app_name'),
])
def test_missing_arguments_fail_instead_of_asking(project, args, flag):
    result = _manage(project, *args)
    assert result.returncode != 0
    assert flag in result.stderr
    assert 'EOFError' not in result.stderr


def test_sdc_cc_without_mixin_flag_does_not_ask(project):
    result = _manage(project, 'sdc_cc', '-a', APP, '-c', 'no_mixin_view')
    assert result.returncode == 0, result.stderr
    assert os.path.isfile(_js(project, 'no_mixin_view'))


def test_sdc_init_answers_no_outside_a_terminal(monkeypatch, capsys):
    from sdc_core.management.commands.sdc_init import Command
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False, raising=False)
    command = Command()
    command._assume_yes = command._assume_no = False
    assert command._yes_no_prompt('Overwrite?') is False


# ------------------------------------------------------------------ WP1.2-1.5: sdc_agent

def test_overview(project):
    result = _manage(project, 'sdc_agent', 'overview')
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert f'app {APP}' in out
    assert f'<shelf-view>  /sdc_view/{APP}/shelf_view  view {APP}/sdc_views.py:' in out
    assert '0 problem(s)' in out
    assert len(out.splitlines()) < 40


def test_where(project):
    result = _manage(project, 'sdc_agent', 'where', '<shelf-view>')
    assert result.returncode == 0, result.stderr
    for part in (f'view       {APP}/sdc_views.py:', f'js         {APP}/Assets/src/{APP}/controller/shelf_view/',
                 f'template   {APP}/templates/{APP}/sdc/shelf_view.html', 'organizer  ', 'js tests   '):
        assert part in result.stdout
    result = _manage(project, 'sdc_agent', 'where', 'nothing_here')
    assert result.returncode != 0 and 'sdc_agent overview' in result.stderr


def test_check_finds_problems(project):
    result = _manage(project, 'sdc_agent', 'check')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'missing documentation' in result.stdout

    organizer, js_path = _organizer(project), _js(project, 'shelf_view')
    organizer_text, js_text = open(organizer).read(), open(js_path).read()
    try:
        with open(organizer, 'w') as f:
            f.write(''.join(line for line in organizer_text.splitlines(keepends=True) if 'shelf_view' not in line))
        with open(js_path, 'w') as f:
            f.write(js_text.replace('super();', "super();\n        this.events.unshift({'click': "
                                                "{'.x': () => this.go()}});", 1))
        result = _manage(project, 'sdc_agent', 'check')
        assert result.returncode == 1
        assert '<shelf-view> is not imported in the app organizer' in result.stdout
        assert 'arrow function registered as event handler in the constructor' in result.stdout
        assert 'fix: add `import {} from "./controller/shelf_view/shelf_view.js";`' in result.stdout
    finally:
        open(organizer, 'w').write(organizer_text)
        open(js_path, 'w').write(js_text)


def test_new_controller(project):
    result = _manage(project, 'sdc_agent', 'new-controller', APP, 'shelf_list')
    assert result.returncode == 0, result.stderr
    assert f'+ {APP}/Assets/src/{APP}/controller/shelf_list/shelf_list.js' in result.stdout
    assert f'~ {APP}/sdc_views.py' in result.stdout and f'~ {APP}/sdc_urls.py' in result.stdout
    assert 'Next:' in result.stdout
    assert '<shelf-list>' in _manage(project, 'sdc_agent', 'overview').stdout


def test_new_model(project):
    result = _manage(project, 'sdc_agent', 'new-model', APP, 'Shelf')
    assert result.returncode == 0, result.stderr
    assert f'~ {APP}/models.py' in result.stdout and 'makemigrations' in result.stdout
    assert 'class Shelf(' in open(os.path.join(project, APP, 'models.py')).read()


# ------------------------------------------------------------------ WP1.6: summaries of tests and builds

DJANGO_OUTPUT = '''Creating test database for alias 'default'...
.F.E
======================================================================
ERROR: test_b (shop.tests.T.test_b)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "shop/tests.py", line 9, in test_b
    x = 1 / 0
ZeroDivisionError: division by zero

======================================================================
FAIL: test_a (shop.tests.T.test_a)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "shop/tests.py", line 5, in test_a
    self.assertEqual(1, 2)
AssertionError: 1 != 2

----------------------------------------------------------------------
Ran 4 tests in 0.010s

FAILED (failures=1, errors=1)
'''

JEST_OUTPUT = '''PASS shop/Assets/tests/a.test.js
FAIL shop/Assets/tests/shop.test.js
  ● Shelf › Load Content

    expect(received).toBeGreaterThan(expected)

    Expected: > 0
    Received:   0

      at Object.<anonymous> (shop/Assets/tests/shop.test.js:12:30)

Test Suites: 1 failed, 1 passed, 2 total
Tests:       1 failed, 7 passed, 8 total
'''


def test_summaries():
    result = runner.summarize_django(runner.RunResult('t', [], 1, 'log'), DJANGO_OUTPUT)
    assert result.summary == 'Ran 4 tests in 0.010s FAILED (failures=1, errors=1)'
    assert result.failures == ['ERROR: test_b (shop.tests.T.test_b)\n    ZeroDivisionError: division by zero',
                               'FAIL: test_a (shop.tests.T.test_a)\n    AssertionError: 1 != 2']
    result = runner.summarize_jest(runner.RunResult('t', [], 1, 'log'), JEST_OUTPUT)
    assert result.summary == 'Test Suites: 1 failed, 1 passed, 2 total | Tests:       1 failed, 7 passed, 8 total'
    assert result.failures[0].startswith('● Shelf › Load Content\n    expect(received).toBeGreaterThan(expected)')
    assert 'at Object' not in result.failures[0]


def test_python_tests_are_summarized(project):
    with open(os.path.join(project, APP, 'tests.py'), 'w') as f:
        f.write('from django.test import SimpleTestCase\n\n\nclass T(SimpleTestCase):\n'
                '    def test_ok(self):\n        pass\n\n    def test_bad(self):\n        self.assertEqual(1, 2)\n')
    result = _manage(project, 'sdc_agent', 'test', APP)
    assert result.returncode == 1
    assert 'test-python: FAILED  Ran 2 tests' in result.stdout
    assert 'AssertionError: 1 != 2' in result.stdout
    assert 'full log: .sdc_agent/logs/test-python.log' in result.stdout
    assert len(result.stdout.splitlines()) < 10


# ------------------------------------------------------------------ M2: agent kit in generated projects

def test_sdc_init_writes_the_agent_kit(project):
    for name in ('AGENTS.md', 'CLAUDE.md', '.claude/skills/sdc-controller/SKILL.md', '.claude/skills/.sdc-kit.json'):
        assert os.path.isfile(os.path.join(project, name)), name
    result = _manage(project, 'sdc_agent', 'kit', 'check')
    assert result.returncode == 0 and 'up to date' in result.stdout


def test_kit_update_fills_the_project_block(project):
    result = _manage(project, 'sdc_agent', 'kit', 'update')
    assert result.returncode == 0, result.stderr
    agents = open(os.path.join(project, 'AGENTS.md')).read()
    assert f'- `{APP}`:' in agents and 'controller(s)' in agents
    assert _manage(project, 'sdc_agent', 'kit', 'install').returncode != 0   # already installed


def test_sdc_init_without_agent_kit(tmp_path):
    path = tmp_path / 'project'
    shutil.copytree('./pytests/test_django_project(DUMMY)', path)
    assert _manage(path, 'sdc_init', '--no-agent-kit').returncode == 0
    assert not (path / 'AGENTS.md').exists() and not (path / '.claude').exists()
