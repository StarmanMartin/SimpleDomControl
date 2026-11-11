"""
The seed of the condition ``free``: the same library app as the SDC seed (``Author``, ``Book``, user ``admin``, three
books, a book detail page), built with plain Django — no SimpleDomControl. The agent may use any framework or
library except SDC. Each project has its own ``.venv`` that sees the packages of the benchmark Python (Django) but
installs new packages locally, so ``pip install`` never changes the benchmark environment.
"""
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
from pathlib import Path

MAIN_APP = 'test_django_project'

MODELS = '''\
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
'''

FORMS = '''\
from django import forms

from library.models import Author, Book


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = "__all__"


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = "__all__"
'''

VIEWS = '''\
from django.shortcuts import get_object_or_404, render

from library.models import Book


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'library/book_detail.html', {'book': book})
'''

URLS = '''\
from django.urls import path

from library import views

urlpatterns = [
    path('books/<int:pk>/', views.book_detail, name='book_detail'),
]
'''

BASE_HTML = '''\
{% load static %}<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{% block title %}Library{% endblock %}</title>
    <style>.d-none { display: none; }</style>
</head>
<body>
{% block content %}{% endblock %}
{% block scripts %}{% endblock %}
</body>
</html>
'''

DETAIL_HTML = '''\
{% extends "library/base.html" %}
{% block title %}{{ book.title }}{% endblock %}
{% block content %}
<h1>{{ book.title }}</h1>
<p>by {{ book.author.name }}</p>
{% endblock %}
'''

GITIGNORE = '''\
__pycache__/
*.pyc
db.sqlite3
.venv/
node_modules/
staticfiles/
'''


def _venv(project):
    """``project/.venv`` that imports the benchmark's packages (Django) but installs its own."""
    venv = Path(project) / '.venv'
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True, capture_output=True)
    python = venv / 'bin' / 'python'
    target = subprocess.run([str(python), '-c', 'import sysconfig; print(sysconfig.get_paths()["purelib"])'],
                            check=True, capture_output=True, text=True).stdout.strip()
    Path(target, '_benchmark_parent.pth').write_text(sysconfig.get_paths()['purelib'] + '\n')
    return python


def create_free_project(task=None, parent=None):
    from project import ADMIN, BOOKS, git, manage
    root = Path(tempfile.mkdtemp(prefix='sdc-agent-bench-free-', dir=parent))
    project = root / 'library_site'
    project.mkdir()
    _venv(project)
    subprocess.run([sys.executable, '-m', 'django', 'startproject', MAIN_APP, '.'], cwd=project, check=True,
                   capture_output=True)
    manage(project, 'startapp', 'library')

    settings_path = project / MAIN_APP / 'settings.py'
    settings = settings_path.read_text()
    settings = settings.replace("    'django.contrib.staticfiles',\n", "    'django.contrib.staticfiles',\n    'library',\n", 1)
    settings = settings.replace('ALLOWED_HOSTS = []', "ALLOWED_HOSTS = ['*']", 1)
    settings_path.write_text(settings)
    urls_path = project / MAIN_APP / 'urls.py'
    urls = urls_path.read_text().replace('from django.urls import path', 'from django.urls import include, path', 1)
    urls = urls.replace("    path('admin/', admin.site.urls),\n",
                        "    path('admin/', admin.site.urls),\n    path('', include('library.urls')),\n", 1)
    urls_path.write_text(urls)

    library = project / 'library'
    (library / 'models.py').write_text(MODELS)
    (library / 'forms.py').write_text(FORMS)
    (library / 'views.py').write_text(VIEWS)
    (library / 'urls.py').write_text(URLS)
    templates = library / 'templates' / 'library'
    templates.mkdir(parents=True)
    (templates / 'base.html').write_text(BASE_HTML)
    (templates / 'book_detail.html').write_text(DETAIL_HTML)
    (library / 'static' / 'library').mkdir(parents=True)

    if task is not None and task.seed is not None:
        task.seed(project)

    manage(project, 'makemigrations', 'library')
    manage(project, 'migrate')
    manage(project, 'shell', '-c', textwrap.dedent(f'''
        from django.contrib.auth import get_user_model
        from library.models import Author, Book
        get_user_model().objects.create_superuser({ADMIN[0]!r}, 'admin@example.org', {ADMIN[1]!r})
        for title, author in {BOOKS!r}:
            Book.objects.create(title=title, author=Author.objects.get_or_create(name=author)[0])
    '''))

    (project / '.gitignore').write_text(GITIGNORE)
    git(project, 'init', '-q')
    git(project, 'config', 'user.email', 'bench@example.org')
    git(project, 'config', 'user.name', 'agent bench')
    git(project, 'add', '-A')
    git(project, 'commit', '-q', '-m', 'seed')
    return project


def used_sdc(project):
    """Project files (not .venv/.git) that use SimpleDomControl."""
    hits = []
    for directory, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in ('.venv', '.git', 'node_modules', '__pycache__')]
        for name in files:
            if not name.endswith(('.py', '.html', '.js', '.json', '.txt', '.toml', '.cfg')):
                continue
            path = Path(directory, name)
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            if 'sdc_core' in text or 'sdc_client' in text or 'SimpleDomControl' in text:
                hits.append(str(path.relative_to(project)))
    return hits
