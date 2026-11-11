"""
The six benchmark tasks for the condition ``free``: the same goals as ``tasks.py``, for the plain Django seed of
``project_free.py``, where the agent may use any framework or library except SimpleDomControl. The checks are
black-box (HTTP requests with the Django test client, database, files), so they do not depend on the chosen stack.
Every check also fails if the project uses SDC.
"""
import json
import re
from pathlib import Path

from tasks import Task, _read, _results

FREE_SUFFIX = ('\n\nThis is a plain Django project. Use any framework or library you like (e.g. Django templates, '
               'htmx, Alpine.js or React from a CDN, Django REST framework or other Python packages: install them '
               'with `python -m pip install`; npm is not available) — but not SimpleDomControl (the Python package '
               '`sdc_core` / `SimpleDomControl` and the JavaScript package `sdc_client`). Work only inside this project '
               'directory. Do not start servers that keep running and do not ask questions: finish the task on your '
               'own.')


def _manage(project, *args):
    from project import manage
    return manage(project, *args)


def _no_sdc(project):
    from project_free import used_sdc
    from django.conf import settings
    hits = used_sdc(project) + [app for app in settings.INSTALLED_APPS if app.startswith('sdc_')]
    return 'no SimpleDomControl', not hits, hits or None


def _client():
    from django.test import Client
    return Client()


def _text(response):
    return response.content.decode(errors='ignore')


# ------------------------------------------------------------------ 1: list page

def check_list(project):
    from library.models import Book
    response = _client().get('/books/')
    html = _text(response) if response.status_code == 200 else ''
    items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.S)
    titles = list(Book.objects.values_list('title', flat=True))
    return _results(
        ('page /books/', response.status_code == 200, f'status {response.status_code}'),
        ('one <li> per title', all(any(t in item for item in items) for t in titles), html[:200] or None),
        _no_sdc(project),
    )


def solve_list(project):
    views = Path(project) / 'library' / 'views.py'
    views.write_text(views.read_text() + '''

def book_list(request):
    return render(request, 'library/book_list.html', {'books': Book.objects.all()})
''')
    urls = Path(project) / 'library' / 'urls.py'
    urls.write_text(urls.read_text().replace(
        "urlpatterns = [\n", "urlpatterns = [\n    path('books/', views.book_list, name='book_list'),\n", 1))
    (Path(project) / 'library' / 'templates' / 'library' / 'book_list.html').write_text(
        '{% extends "library/base.html" %}{% block content %}<ul>{% for book in books %}<li>{{ book.title }}</li>'
        '{% endfor %}</ul>{% endblock %}\n')


# ------------------------------------------------------------------ 2: model with validated forms

def check_review(project):
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    try:
        from library.models import Book, Review
    except ImportError as e:
        return _results(('model', False, str(e)))
    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    try:
        call_command('makemigrations', 'library', '--check', '--dry-run', verbosity=0)
        changes = False
    except SystemExit:
        changes = True
    book = Book.objects.first()
    client = _client()
    before = Review.objects.count()
    client.post('/reviews/new/', {'book': book.pk, 'rating': 6})
    rejected = Review.objects.count() == before
    client.post('/reviews/new/', {'book': book.pk, 'rating': 3})
    created = Review.objects.count() == before + 1
    review = Review.objects.order_by('-pk').first()
    edited = bad_edit_refused = False
    if created and review is not None:
        client.post(f'/reviews/{review.pk}/edit/', {'book': book.pk, 'rating': 0})
        review.refresh_from_db()
        bad_edit_refused = review.rating == 3
        client.post(f'/reviews/{review.pk}/edit/', {'book': book.pk, 'rating': 4})
        review.refresh_from_db()
        edited = review.rating == 4
    return _results(
        ('foreign key to Book', any(getattr(f, 'related_model', None) is Book for f in Review._meta.fields), None),
        ('optional comment', any(f.name == 'comment' and (f.blank or f.null) for f in Review._meta.fields), None),
        ('create page refuses rating 6', rejected, None),
        ('create page creates rating 3', created, None),
        ('edit page refuses rating 0 and saves 4', bad_edit_refused and edited, None),
        ('migrated', not pending and not changes, f'pending={len(pending)} changes={changes}'),
        _no_sdc(project),
    )


def solve_review(project):
    library = Path(project) / 'library'
    models = (library / 'models.py').read_text()
    models = 'from django.core.validators import MaxValueValidator, MinValueValidator\n' + models + '''

class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
'''
    (library / 'models.py').write_text(models)
    forms = (library / 'forms.py').read_text().replace('import Author, Book', 'import Author, Book, Review')
    (library / 'forms.py').write_text(forms + '''

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = "__all__"
''')
    (library / 'views.py').write_text((library / 'views.py').read_text() + '''

def review_form(request, pk=None):
    from django.shortcuts import redirect
    from library.forms import ReviewForm
    from library.models import Review
    instance = get_object_or_404(Review, pk=pk) if pk else None
    form = ReviewForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('/books/')
    return render(request, 'library/review_form.html', {'form': form})
''')
    (library / 'templates' / 'library' / 'review_form.html').write_text(
        '{% extends "library/base.html" %}{% block content %}<form method="post">{% csrf_token %}{{ form.as_p }}'
        '<button>Save</button></form>{% endblock %}\n')
    urls = (library / 'urls.py').read_text().replace("urlpatterns = [\n", "urlpatterns = [\n"
        "    path('reviews/new/', views.review_form),\n    path('reviews/<int:pk>/edit/', views.review_form),\n", 1)
    (library / 'urls.py').write_text(urls)
    _manage(project, 'makemigrations', 'library')
    _manage(project, 'migrate')


# ------------------------------------------------------------------ 3: server call from a button

def check_count(project):
    from library.models import Book
    client = _client()
    book = Book.objects.first()
    page = client.get(f'/books/{book.pk}/')
    html = _text(page)
    count = Book.objects.count()
    answer = client.get('/api/book-count/')
    if answer.status_code == 405:
        answer = client.post('/api/book-count/')
    try:
        value = json.loads(answer.content).get('count')
    except (ValueError, AttributeError):
        value = None
    scripts = html + ''.join(p.read_text(errors='ignore') for p in Path(project).glob('library/static/**/*.js'))
    return _results(
        ('endpoint returns the count', value == count, f'status {answer.status_code}, count {value!r}'),
        ('button "Count books"', bool(re.search(r'<button[^>]*>\s*Count books\s*</button>', html)), None),
        ('book-count element', 'book-count' in html, None),
        ('page code calls the endpoint', '/api/book-count' in scripts or 'book-count/' in scripts, None),
        _no_sdc(project),
    )


def solve_count(project):
    library = Path(project) / 'library'
    (library / 'views.py').write_text((library / 'views.py').read_text() + '''

def book_count(request):
    from django.http import JsonResponse
    return JsonResponse({'count': Book.objects.count()})
''')
    urls = (library / 'urls.py').read_text().replace("urlpatterns = [\n",
                                                    "urlpatterns = [\n    path('api/book-count/', views.book_count),\n", 1)
    (library / 'urls.py').write_text(urls)
    detail = library / 'templates' / 'library' / 'book_detail.html'
    head, endblock, tail = detail.read_text().rpartition('{% endblock %}')   # end of the content block
    detail.write_text(head + COUNT_SNIPPET + endblock + tail)


COUNT_SNIPPET = """<button type="button" id="count">Count books</button> <span class="book-count"></span>
<script>
document.getElementById('count').addEventListener('click', () => fetch('/api/book-count/')
    .then((r) => r.json()).then((data) => { document.querySelector('.book-count').textContent = data.count; }));
</script>
"""


# ------------------------------------------------------------------ 4: fix a broken widget

COUNTER_JS = '''class BookCounter {
    constructor(root) {
        this.root = root;
        root.querySelector('.more').addEventListener('click', this.toggle);
    }

    toggle() {
        this.root.querySelector('.extra').classList.toggle('d-none');
    }
}

document.querySelectorAll('.book-counter').forEach((element) => new BookCounter(element));
'''

COUNTER_HTML = '''{% extends "library/base.html" %}
{% load static %}
{% block content %}
<div class="book-counter">
    <p>There are books.</p>
    <button type="button" class="more">Show more</button>
    <p class="extra d-none">Dune, Emma and Ulysses.</p>
</div>
{% endblock %}
'''


def seed_counter(project):
    library = Path(project) / 'library'
    (library / 'static' / 'library' / 'counter.js').write_text(COUNTER_JS)
    (library / 'templates' / 'library' / 'counter.html').write_text(COUNTER_HTML)
    (library / 'views.py').write_text((library / 'views.py').read_text() + '''

def counter(request):
    return render(request, 'library/counter.html')
''')
    urls = (library / 'urls.py').read_text().replace("urlpatterns = [\n",
                                                    "urlpatterns = [\n    path('counter/', views.counter),\n", 1)
    (library / 'urls.py').write_text(urls)


def check_counter(project):
    html = _text(_client().get('/counter/'))
    js = _read(project, 'library/static/library/counter.js')
    included = 'library/counter.js' in html or 'class BookCounter' in html
    code = js + html
    unbound = re.search(r'''addEventListener\(\s*['"]click['"]\s*,\s*this\.\w+\s*\)''', code)
    toggles = 'd-none' in code and 'toggle' in code
    return _results(
        ('script included in the page', included, None),
        ('click handler keeps `this`', not unbound and toggles, None),
        _no_sdc(project),
    )


def solve_counter(project):
    library = Path(project) / 'library'
    template = library / 'templates' / 'library' / 'counter.html'
    template.write_text(template.read_text().replace(
        '{% endblock %}\n', '{% endblock %}\n{% block scripts %}<script src="{% static \'library/counter.js\' %}">'
        '</script>{% endblock %}\n'))
    js = library / 'static' / 'library' / 'counter.js'
    js.write_text(js.read_text().replace("addEventListener('click', this.toggle)",
                                         "addEventListener('click', () => this.toggle())"))


# ------------------------------------------------------------------ 5: MCP access with a token

def _mcp(client, token, method, params=None, id=1):
    headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'} if token else {}
    body = {'jsonrpc': '2.0', 'id': id, 'method': method, **({'params': params} if params else {})}
    response = client.post('/mcp/', json.dumps(body), content_type='application/json',
                           HTTP_ACCEPT='application/json, text/event-stream', **headers)
    text = _text(response)
    if 'data:' in text and response.get('Content-Type', '').startswith('text/event-stream'):
        text = next((line[5:].strip() for line in text.splitlines() if line.startswith('data:')), '')
    try:
        return response.status_code, json.loads(text)
    except ValueError:
        return response.status_code, None


def check_mcp(project):
    from library.models import Book
    token = _read(project, 'mcp_token.txt').strip()
    client = _client()
    status, init = _mcp(client, token, 'initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                                      'clientInfo': {'name': 'bench', 'version': '1'}})
    _status, listed = _mcp(client, token, 'tools/list', id=2)
    tools = ((listed or {}).get('result') or {}).get('tools') or []
    titles = list(Book.objects.values_list('title', flat=True))
    returns_books = False
    for tool in tools:
        required = (tool.get('inputSchema') or {}).get('required') or []
        if required:
            continue
        _s, called = _mcp(client, token, 'tools/call', {'name': tool['name'], 'arguments': {}}, id=3)
        if called and all(t in json.dumps(called) for t in titles):
            returns_books = True
            break
    anon_status, anon = _mcp(client, '', 'tools/list', id=4)
    anonymous_refused = anon_status in (401, 403) or (anon is not None and 'error' in anon)
    writes = [t['name'] for t in tools if re.search(r'create|update|delete|write|save|add|remove', t['name'], re.I)]
    return _results(
        ('token file', bool(token), None),
        ('MCP initialize', status == 200 and init is not None and 'result' in init, f'status {status}'),
        ('a tool lists the books', returns_books, [t['name'] for t in tools] or None),
        ('read-only (no write tools)', not writes, writes or None),
        ('without token refused', anonymous_refused, f'status {anon_status}'),
        _no_sdc(project),
    )


def solve_mcp(project):
    library = Path(project) / 'library'
    (library / 'mcp.py').write_text('''import json
import secrets

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from library.models import Book

TOKEN_FILE = 'mcp_token.txt'


def _token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


@csrf_exempt
def mcp(request):
    if request.headers.get('Authorization') != f'Bearer {_token()}':
        return JsonResponse({'error': 'unauthorized'}, status=401)
    message = json.loads(request.body)
    if 'id' not in message:
        return HttpResponse(status=202)
    method, id = message.get('method'), message['id']
    if method == 'initialize':
        result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'library', 'version': '1'}}
    elif method == 'tools/list':
        result = {'tools': [{'name': 'list_books', 'description': 'All books',
                             'inputSchema': {'type': 'object', 'properties': {}}}]}
    elif method == 'tools/call':
        books = [{'id': b.pk, 'title': b.title} for b in Book.objects.all()]
        result = {'content': [{'type': 'text', 'text': json.dumps(books)}]}
    else:
        return JsonResponse({'jsonrpc': '2.0', 'id': id, 'error': {'code': -32601, 'message': 'not found'}})
    return JsonResponse({'jsonrpc': '2.0', 'id': id, 'result': result})
''')
    urls = (library / 'urls.py').read_text().replace("from library import views\n",
                                                    "from library import mcp, views\n", 1)
    urls = urls.replace("urlpatterns = [\n", "urlpatterns = [\n    path('mcp/', mcp.mcp),\n", 1)
    (library / 'urls.py').write_text(urls)
    import secrets
    (Path(project) / 'mcp_token.txt').write_text(secrets.token_urlsafe(24) + '\n')


# ------------------------------------------------------------------ 6: documentation for an AI assistant

def check_document(project):
    from library import models
    texts = [p.read_text(errors='ignore') for p in Path(project).rglob('*.md')
             if '.venv' not in p.parts and '.git' not in p.parts]
    texts += [cls.__doc__ or '' for cls in (models.Author, models.Book)]
    for module in ('library.views', 'library.urls'):
        try:
            import importlib
            texts.append(importlib.import_module(module).__doc__ or '')
            texts += [getattr(obj, '__doc__', '') or '' for obj in vars(importlib.import_module(module)).values()
                      if callable(obj) and getattr(obj, '__module__', '') == module]
        except ImportError:
            pass
    text = '\n'.join(texts)
    needed = {'Author': 'name', 'Book': 'title'}
    models_ok = all(name in text and field in text for name, field in needed.items())
    pages_ok = '/books/' in text
    return _results(
        ('models documented (Author: name, Book: title)', models_ok, None),
        ('book page documented (/books/…)', pages_ok, None),
        _no_sdc(project),
    )


def solve_document(project):
    (Path(project) / 'AI.md').write_text('''# Library app for AI assistants

- `Author`: an author of books; field `name`.
- `Book`: a book with a `title`, written by one `Author` (`author`).
- `/books/<id>/`: the detail page of one book (title and author).
''')


FREE_TASKS = [
    Task('controller_list',
         'In the Django app `library`, add a page at `/books/` that shows the titles of all `Book` records as a list '
         '(`<ul>` with one `<li>` per title). The titles must be in the HTML of the page (visible without running '
         'JavaScript).',
         check_list, solve_list, suffix=FREE_SUFFIX),
    Task('model_review',
         'Add a data model `Review` to the app `library`: it belongs to a `Book` (foreign key), has an integer '
         '`rating` from 1 to 5 and an optional text `comment`. Add an HTML form page to create a review at '
         '`/reviews/new/` and one to edit a review at `/reviews/<id>/edit/` (form fields `book`, `rating`, '
         '`comment`, sent with POST; no login needed). Both must only accept ratings from 1 to 5. Apply the database '
         'migration.',
         check_review, solve_review, suffix=FREE_SUFFIX),
    Task('server_call',
         'The book detail page (`/books/<id>/`) needs a button "Count books". When the user clicks it, the browser '
         'asks the server for the number of `Book` records without reloading the page — through an endpoint '
         '`/api/book-count/` that answers JSON `{"count": <number>}` — and shows the number in an element with the '
         'CSS class `book-count`.',
         check_count, solve_count, suffix=FREE_SUFFIX),
    Task('fix_counter',
         'The book counter on the page `/counter/` (app `library`) does not work: its script never runs, and once '
         'that is fixed its "Show more" button does nothing. Find and fix the causes.',
         check_counter, solve_counter, seed=seed_counter, suffix=FREE_SUFFIX),
    Task('mcp_token',
         'Make the `Book` data of this project available to AI clients over MCP (Model Context Protocol, Streamable '
         'HTTP transport: JSON-RPC over POST), read-only: an MCP endpoint at `/mcp/` with a tool that lists the '
         'books, protected by a bearer token. Create a token for the user `admin` that can only read `Book` records '
         'and write the token (nothing else) into the file `mcp_token.txt` in the project root.',
         check_mcp, solve_mcp, suffix=FREE_SUFFIX),
    Task('document',
         'Prepare this project for an AI assistant that should help users of the app: document the models `Author` '
         'and `Book` (what they are, their fields) and the pages of the app (URL and what they show), so that an '
         'assistant reading the documentation can find its way. Put it where an assistant would find it (docstrings '
         'or a Markdown file in the project).',
         check_document, solve_document, suffix=FREE_SUFFIX),
]

FREE_BY_ID = {task.id: task for task in FREE_TASKS}
