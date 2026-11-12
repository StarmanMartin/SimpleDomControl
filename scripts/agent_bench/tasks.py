"""
Benchmark tasks (see projects/agents.plan.md, WP0.1). Each task has

- ``prompt``: what the agent is asked; it describes the result, not the commands to use
- ``seed(project)``: optional extra seed, before migrations and the seed commit
- ``check(project)``: runs inside the project (Django set up by ``run_check.py``); returns ``(passed, details)``
- ``solve(project)``: a reference solution for ``bench.py selftest`` (check fails before, passes after)

Nothing here imports Django at module level: the module is also imported by the harness process.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

SUFFIX = ('\n\nThis is a Django project built with the SimpleDomControl (SDC) framework (Python package '
          '`sdc_core`, JavaScript runtime `sdc_client`). Work only inside this project directory. Do not start '
          'servers that keep running and do not ask questions: finish the task on your own.')

LIB = 'library'
CTRL_DIR = Path(LIB) / 'Assets' / 'src' / LIB / 'controller'
ORGANIZER = Path(LIB) / 'Assets' / 'src' / LIB / f'{LIB}.organizer.js'
TEMPLATES = Path(LIB) / 'templates' / LIB / 'sdc'
VIEWS = Path(LIB) / 'sdc_views.py'


@dataclass
class Task:
    id: str
    prompt: str
    check: Callable
    solve: Callable
    seed: Optional[Callable] = None
    suffix: Optional[str] = None

    @property
    def full_prompt(self):
        return self.prompt + (self.suffix or SUFFIX)


def _read(project, path):
    path = Path(project) / path
    return path.read_text() if path.exists() else ''


def _manage(project, *args):
    from project import manage
    return manage(project, *args)


def _replace_in_class(source, class_name, old, new):
    """Replaces ``old`` with ``new`` inside the body of ``class_name`` (up to the next top-level class)."""
    start = source.index(f'class {class_name}(')
    end = source.find('\nclass ', start + 1)
    end = len(source) if end == -1 else end
    body = source[start:end]
    assert old in body, (class_name, old)
    return source[:start] + body.replace(old, new, 1) + source[end:]


def _results(*checks):
    """``checks``: (name, passed, detail) → (passed, details)."""
    details = {name: {'ok': bool(ok), **({'detail': detail} if detail else {})} for name, ok, detail in checks}
    return all(c[1] for c in checks), details


def _content(url, user=None):
    from django.test import Client
    client = Client()
    if user is not None:
        client.force_login(user)
    response = client.get(url, {'_method': 'content'})
    if response.status_code != 200:
        return None, f'status {response.status_code}'
    try:
        return json.loads(response.content)['html'], None
    except (ValueError, KeyError):
        return response.content.decode(), None


# ------------------------------------------------------------------ 1: new controller

def check_controller_list(project):
    from library.models import Book
    js = _read(project, CTRL_DIR / 'book_list' / 'book_list.js')
    titles = list(Book.objects.values_list('title', flat=True))
    html, problem = _content('/sdc_view/library/book_list')
    server_rendered = html is not None and '<li' in html and all(t in html for t in titles)
    client_rendered = bool(re.search(r'''querySet\(\s*['"]Book['"]''', js)) and '<li' in (js + (html or ''))
    return _results(
        ('view', html is not None, problem),
        ('js', 'sdc_view/library/book_list' in js and 'app.register' in js, None),
        ('organizer', 'controller/book_list/book_list.js' in _read(project, ORGANIZER), None),
        ('renders titles', server_rendered or client_rendered, None if server_rendered or client_rendered
         else (html or '')[:200]),
    )


def solve_controller_list(project):
    _manage(project, 'sdc_cc', '-a', LIB, '-c', 'book_list', '-m', '')
    views = _read(project, VIEWS)
    views = _replace_in_class(views, 'BookList', 'return render(request, self.template_name), {}',
                              'from library.models import Book\n'
                              '        return render(request, self.template_name, {"books": Book.objects.all()}), {}')
    (Path(project) / VIEWS).write_text(views)
    (Path(project) / TEMPLATES / 'book_list.html').write_text(
        '<ul>{% for book in books %}<li>{{ book.title }}</li>{% endfor %}</ul>\n')


# ------------------------------------------------------------------ 2: new model

def check_model_review(project):
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    try:
        from library.models import Book, Review
    except ImportError as e:
        return _results(('model', False, str(e)))
    from sdc_core.sdc_extentions.models import resolve_form
    fk = next((f.name for f in Review._meta.fields if getattr(f, 'related_model', None) is Book), None)
    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    try:
        call_command('makemigrations', LIB, '--check', '--dry-run', verbosity=0)
        changes = False
    except SystemExit:
        changes = True
    forms_ok, detail = False, None
    try:
        create = resolve_form(Review.SdcMeta.create_form)
        edit = resolve_form(Review.SdcMeta.edit_form)
        book = Book.objects.first()
        too_high = create(data={fk: book.pk, 'rating': 6})
        too_low = edit(data={fk: book.pk, 'rating': 0})
        fine = create(data={fk: book.pk, 'rating': 3})
        forms_ok = (not too_high.is_valid() and 'rating' in too_high.errors and not too_low.is_valid()
                    and fine.is_valid())
        detail = None if forms_ok else {'fine': fine.errors.get_json_data(), 'too_high': too_high.is_valid()}
    except Exception as e:  # noqa: BLE001 - any problem of the agent's code fails the check
        detail = repr(e)
    return _results(
        ('sdc model', getattr(Review, '__is_sdc_model__', False), None),
        ('foreign key to Book', fk is not None, None),
        ('optional comment', any(f.name == 'comment' and (f.blank or f.null) for f in Review._meta.fields), None),
        ('forms validate rating 1-5', forms_ok, detail),
        ('migrated', not pending and not changes, f'pending={len(pending)} changes={changes}'),
    )


def solve_model_review(project):
    models = _read(project, Path(LIB) / 'models.py')
    models = models.replace('from django.db import models\n',
                            'from django.core.validators import MaxValueValidator, MinValueValidator\n'
                            'from django.db import models\n', 1)
    models += '''

class Review(models.Model, SdcModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    class SdcMeta:
        edit_form = "library.forms.ReviewForm"
        create_form = "library.forms.ReviewForm"

    @classmethod
    def is_authorised(cls, user, action, obj):
        return True

    @classmethod
    def get_queryset(cls, user, action, obj):
        return cls.objects.all()
'''
    (Path(project) / LIB / 'models.py').write_text(models)
    forms = _read(project, Path(LIB) / 'forms.py').replace('import Author, Book', 'import Author, Book, Review')
    forms += '''

class ReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = "__all__"
'''
    (Path(project) / LIB / 'forms.py').write_text(forms)
    _manage(project, 'makemigrations', LIB)
    _manage(project, 'migrate')


# ------------------------------------------------------------------ 3: server call

def check_server_call(project):
    from django.test import Client
    from library.models import Book
    js = _read(project, CTRL_DIR / 'book_detail' / 'book_detail.js')
    template = _read(project, TEMPLATES / 'book_detail.html')
    response = Client().post('/sdc_view/library/book_detail', {
        '_method': 'sdc_server_call', '_sdc_func_name': 'count_books', 'data': '{}'})
    count = Book.objects.count()
    value = None
    if response.status_code == 200:
        try:
            value = json.loads(response.content).get('_return_data')
        except ValueError:
            value = response.content.decode()
    returned = value == count or (isinstance(value, dict) and count in value.values()) or \
        (isinstance(value, str) and str(count) in value)
    return _results(
        ('server call returns the count', returned, f'status {response.status_code}, value {value!r}'),
        ('button', '<button' in template or '<button' in js, None),
        ('book-count element', 'book-count' in template or 'book-count' in js, None),
        ('client calls count_books', bool(re.search(r'''serverCall\(\s*['"]count_books['"]''', js)), None),
    )


def solve_server_call(project):
    views = _read(project, VIEWS)
    views = _replace_in_class(views, 'BookDetail', '    def get_content(', '''    def count_books(self, channel, **kwargs):
        from library.models import Book
        return Book.objects.count()

    def get_content(''')
    (Path(project) / VIEWS).write_text(views)
    (Path(project) / TEMPLATES / 'book_detail.html').write_text(
        '<button type="button" sdc_click="show_count">Count books</button> <span class="book-count"></span>\n')
    js_path = Path(project) / CTRL_DIR / 'book_detail' / 'book_detail.js'
    js = js_path.read_text()
    js = js.replace('    onRefresh() {', '''    show_count() {
        return this.serverCall('count_books').then((count) => this.find('.book-count').text(count));
    }

    onRefresh() {''', 1)
    js_path.write_text(js)


# ------------------------------------------------------------------ 4: fix a broken controller

COUNTER_JS = '''import {AbstractSDC, app} from 'sdc_client';


class BookCounterController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/library/book_counter"; //<book-counter></book-counter>
        this.events.unshift({'click': {'.more': () => this.toggle()}});
    }

    onLoad($html) {
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    toggle() {
        this.find('.extra').toggleClass('d-none');
    }

}

app.register(BookCounterController);
'''


def seed_fix_counter(project):
    _manage(project, 'sdc_cc', '-a', LIB, '-c', 'book_counter', '-m', '')
    (Path(project) / CTRL_DIR / 'book_counter' / 'book_counter.js').write_text(COUNTER_JS)
    (Path(project) / TEMPLATES / 'book_counter.html').write_text(
        '<p>There are books.</p>\n<button type="button" class="more">Show more</button>\n'
        '<p class="extra d-none">Dune, Emma and Ulysses.</p>\n')
    organizer = Path(project) / ORGANIZER
    organizer.write_text(''.join(line for line in organizer.read_text().splitlines(keepends=True)
                                 if 'book_counter' not in line))


def _enclosing_method(js, position):
    """Name of the class method whose body contains ``position`` (the last method header before it)."""
    headers = list(re.finditer(r'^\s{4}(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', js[:position], re.M))
    return headers[-1].group(1) if headers else None


def check_fix_counter(project):
    js = _read(project, CTRL_DIR / 'book_counter' / 'book_counter.js')
    template = _read(project, TEMPLATES / 'book_counter.html')
    # SDC calls event handlers on the controller instance of the page; the constructor runs on another object, so
    # an arrow function created there captures the wrong `this`. Arrow functions created in willShow/onLoad (the
    # live instance; events are bound after willShow) work.
    arrow = re.search(r'''['"]\.more['"]\s*:\s*\([^)]*\)\s*=>\s*\{?\s*this\.''', js)
    arrow_in_constructor = arrow is not None and _enclosing_method(js, arrow.start()) == 'constructor'
    bound = re.search(r'''['"]\.more['"]\s*:\s*(function\b|this\.\w+\.bind\(this\)|this\.\w+\b(?!\s*\())''', js) or \
        re.search(r'sdc_click\s*=\s*"\w+"', template) or (arrow is not None and not arrow_in_constructor)
    arrow_handler = arrow_in_constructor
    return _results(
        ('registered in the organizer', 'controller/book_counter/book_counter.js' in _read(project, ORGANIZER),
         None),
        ('click handler gets the controller', bool(bound) and not arrow_handler, None),
        ('toggle still there', 'toggle' in js or 'd-none' in js, None),
    )


def solve_fix_counter(project):
    organizer = Path(project) / ORGANIZER
    organizer.write_text('import {} from "./controller/book_counter/book_counter.js";\n' + organizer.read_text())
    js_path = Path(project) / CTRL_DIR / 'book_counter' / 'book_counter.js'
    js_path.write_text(js_path.read_text().replace("'.more': () => this.toggle()",
                                                   "'.more': function () { this.toggle(); }"))


# ------------------------------------------------------------------ 5: MCP access with a token

def check_mcp_token(project):
    from django.test import Client
    from sdc_core.api_tokens import hash_token
    from sdc_core.mcp.settings import exposed_models, mcp_settings
    from sdc_core.models import ApiToken
    secret = _read(project, 'mcp_token.txt').strip()
    token = ApiToken.objects.filter(secret_hash=hash_token(secret)).select_related('user').first() if secret else None
    tools = None
    if token is not None:
        response = Client(headers={'Authorization': f'Bearer {secret}'}).post(
            '/sdc_mcp/', json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}),
            content_type='application/json')
        if response.status_code == 200:
            tools = json.loads(response.content).get('result', {}).get('tools')
    load = next((t for t in tools or [] if t['name'] == 'model_load'), None)
    return _results(
        ('endpoint enabled', mcp_settings()['enabled'], None),
        ('only Book exposed', exposed_models() == ['Book'], str(exposed_models())),
        ('token of admin', token is not None and token.user.username == 'admin' and token.is_valid, None),
        ('token reads only Book', token is not None and token.privileges == ['model:Book:read'],
         token.privileges if token else None),
        ('MCP lists Book', load is not None and load['inputSchema']['properties']['model']['enum'] == ['Book'],
         None if tools else 'no tools/list answer'),
    )


def solve_mcp_token(project):
    settings_path = Path(project) / 'test_django_project' / 'settings.py'
    text = settings_path.read_text()
    text = re.sub(r"SDC_MCP = \{.*?\n\}", "SDC_MCP = {\n    'enabled': True,\n    'models': ['Book'],\n"
                  "    'max_records': 50,\n}", text, count=1, flags=re.S)
    settings_path.write_text(text)
    out = _manage(project, 'sdc_tokens', 'create', '--user', 'admin', '--name', 'mcp',
                  '--privileges', 'model:Book:read').stdout
    (Path(project) / 'mcp_token.txt').write_text(out.strip().splitlines()[-1] + '\n')


# ------------------------------------------------------------------ 6: documentation for the AI assistant

def check_document(project):
    import io
    from django.core.management import call_command
    out = io.StringIO()
    call_command('sdc_prepare_teaching', stdout=out)
    text = out.getvalue()
    section = text.split('## Undocumented', 1)[1] if '## Undocumented' in text else ''
    missing = [line.strip() for line in section.splitlines() if f'({LIB})' in line]
    return _results(('nothing undocumented in library', not missing, missing or None))


def solve_document(project):
    models_path = Path(project) / LIB / 'models.py'
    models = models_path.read_text()
    models = models.replace('class Author(models.Model, SdcModel):\n',
                            'class Author(models.Model, SdcModel):\n'
                            '    """An author of books; `name` is required. Anyone may read and change authors."""\n')
    models = models.replace('class Book(models.Model, SdcModel):\n',
                            'class Book(models.Model, SdcModel):\n'
                            '    """A book with a `title`, written by one `Author`. Anyone may read and change '
                            'books."""\n')
    models_path.write_text(models)
    js_path = Path(project) / CTRL_DIR / 'book_detail' / 'book_detail.js'
    js_path.write_text(js_path.read_text().replace(
        'class BookDetailController', '/**\n * Shows the details of one book.\n */\nclass BookDetailController', 1))


TASKS = [
    Task('controller_list',
         'In the Django app `library`, add a new SDC controller with the tag `<book-list>` that shows the titles '
         'of all `Book` records as a list (`<ul>` with one `<li>` per title). Follow the framework\'s conventions '
         'so that it works like the existing `<book-detail>` controller.',
         check_controller_list, solve_controller_list),
    Task('model_review',
         'Add a data model `Review` to the app `library`: it belongs to a `Book` (foreign key), has an integer '
         '`rating` from 1 to 5 and an optional text `comment`. Make it an SDC model whose records can be created '
         'and edited through SDC forms (create form and edit form); the forms must only accept ratings from 1 to '
         '5. Apply the database migration.',
         check_model_review, solve_model_review),
    Task('server_call',
         'The controller `<book-detail>` in the app `library` needs a button "Count books". When the user clicks '
         'it, the browser calls a server method `count_books` of the controller\'s Django view, which returns the '
         'number of `Book` records, and the controller shows that number in an element with the CSS class '
         '`book-count`.',
         check_server_call, solve_server_call),
    Task('fix_counter',
         'The controller `<book-counter>` in the app `library` does not work: wherever it is used, nothing of it '
         'appears, and once that is fixed its "Show more" button does nothing. Find and fix the causes.',
         check_fix_counter, solve_fix_counter, seed=seed_fix_counter),
    Task('mcp_token',
         'Make the `Book` data of this project available to AI clients over MCP, read-only: enable the MCP '
         'endpoint, expose only the `Book` model, and create an API token for the user `admin` that can only read '
         '`Book` records. Write the token (nothing else) into the file `mcp_token.txt` in the project root.',
         check_mcp_token, solve_mcp_token),
    Task('document',
         'Prepare this project for the SDC AI assistant: the models `Author` and `Book` and the controllers of the '
         'app `library` are not documented. Document them the way SDC expects, so that SDC\'s own tooling reports '
         'nothing undocumented for the app `library`.',
         check_document, solve_document),
]

BY_ID = {task.id: task for task in TASKS}


def tasks_for(condition):
    """``{id: Task}`` of a condition: ``free`` (any framework except SDC) has its own versions of the tasks."""
    if condition == 'free':
        from tasks_free import FREE_BY_ID
        return FREE_BY_ID
    return BY_ID
