"""
Builds a fresh, seeded SDC project for one benchmark run (see projects/agents.architecture.md, section 3).

The project is a copy of ``pytests/test_django_project(DUMMY)`` after ``sdc_init``, plus an app ``library`` with the
SdcModels ``Author`` and ``Book``, the controller ``<book-detail>``, a user ``admin`` and a few books. It lives in a
new temporary directory outside any repository and is committed to a local git repository, so the changes of the
agent can be measured.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DUMMY = REPO / 'pytests' / 'test_django_project(DUMMY)'
MAIN_APP = 'test_django_project'
ADMIN = ('admin', 'admin-Pa55word')
BOOKS = [('Dune', 'Frank Herbert'), ('Emma', 'Jane Austen'), ('Ulysses', 'James Joyce')]

MODELS = '''\
from django.db import models

from sdc_core.sdc_extentions.models import SdcModel


class Author(models.Model, SdcModel):
    name = models.CharField(max_length=255)

    class SdcMeta:
        edit_form = "library.forms.AuthorForm"
        create_form = "library.forms.AuthorForm"

    def __str__(self):
        return self.name

    @classmethod
    def is_authorised(cls, user, action, obj):
        return True

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()


class Book(models.Model, SdcModel):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    class SdcMeta:
        edit_form = "library.forms.BookForm"
        create_form = "library.forms.BookForm"

    def __str__(self):
        return self.title

    @classmethod
    def is_authorised(cls, user, action, obj):
        return True

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()
'''

FORMS = '''\
from django.forms.models import ModelForm

from library.models import Author, Book


class AuthorForm(ModelForm):
    class Meta:
        model = Author
        fields = "__all__"


class BookForm(ModelForm):
    class Meta:
        model = Book
        fields = "__all__"
'''

GITIGNORE = '''\
__pycache__/
*.pyc
db.sqlite3
node_modules/
.sdc_agent/
'''


def python():
    """The Python of the benchmark (with SimpleDomControl installed); also the agent's ``python``."""
    return sys.executable


def project_python(project):
    """The project's own ``.venv`` interpreter (condition ``free``), else the benchmark Python."""
    venv = Path(project) / '.venv' / 'bin' / 'python'
    return str(venv) if venv.exists() else python()


def env_for(project):
    """Environment for commands in the project: its Python first on PATH, no settings module of the caller."""
    env = dict(os.environ)
    env.pop('DJANGO_SETTINGS_MODULE', None)
    env.pop('VIRTUAL_ENV', None)
    env['PATH'] = os.path.dirname(project_python(project)) + os.pathsep + env.get('PATH', '')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def manage(project, *args, check=True):
    result = subprocess.run([project_python(project), 'manage.py', *args], cwd=project, env=env_for(project),
                            stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f'manage.py {" ".join(args)} failed:\n{result.stdout}\n{result.stderr}')
    return result


def git(project, *args):
    return subprocess.run(['git', *args], cwd=project, capture_output=True, text=True, check=True).stdout


def create_project(task=None, condition='baseline', parent=None):
    """Creates a seeded project and returns its path. ``task.seed(project)`` adds the task's own seed."""
    if condition == 'free':
        from project_free import create_free_project
        return create_free_project(task, parent)
    root = Path(tempfile.mkdtemp(prefix='sdc-agent-bench-', dir=parent))
    project = root / 'library_site'
    shutil.copytree(DUMMY, project)
    (project / 'db.sqlite3').unlink(missing_ok=True)
    # The agent kit is part of the condition, not of the seed (sdc_init would install it by default)
    manage(project, 'sdc_init', '--no-agent-kit')

    manage(project, 'startapp', 'library')
    base_settings = project / MAIN_APP / 'base_settings.py'
    text = base_settings.read_text()
    text = text.replace('    "test_app_two",\n', '    "test_app_two",\n    "library",\n', 1)
    base_settings.write_text(text)
    (project / 'library' / 'models.py').write_text(MODELS)
    (project / 'library' / 'forms.py').write_text(FORMS)
    manage(project, 'sdc_cc', '-a', 'library', '-c', 'book_detail', '-m', '')

    if task is not None and task.seed is not None:
        task.seed(project)

    manage(project, 'makemigrations', 'library')
    manage(project, 'migrate')
    seed_data = textwrap.dedent(f'''
        from django.contrib.auth import get_user_model
        from library.models import Author, Book
        get_user_model().objects.create_superuser({ADMIN[0]!r}, 'admin@example.org', {ADMIN[1]!r})
        for title, author in {BOOKS!r}:
            Book.objects.create(title=title, author=Author.objects.get_or_create(name=author)[0])
    ''')
    manage(project, 'shell', '-c', seed_data)

    if condition == 'kit':
        manage(project, 'sdc_agent', 'kit', 'install')
    elif condition != 'baseline':
        raise ValueError(f'Unknown condition {condition}')

    (project / '.gitignore').write_text(GITIGNORE)
    git(project, 'init', '-q')
    git(project, 'config', 'user.email', 'bench@example.org')
    git(project, 'config', 'user.name', 'agent bench')
    git(project, 'add', '-A')
    git(project, 'commit', '-q', '-m', 'seed')
    return project


def changed_files(project):
    """Files the agent added, changed or deleted since the seed commit (paths relative to the project)."""
    git(project, 'add', '-A')
    out = git(project, 'diff', '--cached', '--name-status', 'HEAD')
    return [line.split('\t', 1)[-1] for line in out.splitlines() if line.strip()]


def remove_project(project):
    shutil.rmtree(Path(project).parent, ignore_errors=True)
