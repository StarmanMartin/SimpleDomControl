import ast
import inspect
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from sdc_core.management.commands.utils.teach_crawler import merge_crawls  # noqa: E402
from sdc_core.management.commands.utils.teach_markdown import render_skill  # noqa: E402


def _node(path, args=None, seen_as='anonymous', error_code=None, **kwargs):
    args = args or {}
    return {
        'key': '~'.join(path) + '?' + ','.join(sorted(args)),
        'href': '/~' + '~'.join(path),
        'path': path,
        'nav_idx': len(path) - 1,
        'args': {k: [v] for k, v in args.items()},
        'depth': len(path) - 1,
        'via': 'start',
        'seen_as': {seen_as},
        'error_code': error_code,
        'headings': [],
        'controllers': [{'tag': path[-1], 'url_params': [], 'parent': None, 'nav_idx': len(path) - 1}],
        'url_params': [],
        'links': [],
        'external': [],
        'forms': [],
        'buttons': [],
    } | kwargs


def _tree(*nodes):
    return {'nodes': {n['key']: n for n in nodes}, 'errors': [],
            'global': {'links': [], 'buttons': [], 'forms': [], 'external': []}}


def _render(tree):
    return render_skill(tree, {'project': 'Demo', 'crawled_as': ['anonymous'], 'logged_in_label': 'user admin',
                               'date': '2026-01-01'})


def test_tree_nesting_and_args():
    md = _render(_tree(
        _node(['main-view']),
        _node(['main-view', 'book-edit'], {'2.pk': 3, '2.edit': True}),
    ))
    assert md.startswith('---\nname: demo-ui\n')
    assert '- **main-view** — `/~main-view`' in md
    assert '  - **book-edit** — `/~main-view~book-edit`' in md
    assert '`2.pk` (number), e.g. `3`' in md
    assert '`2.edit` (bool), e.g. `True`' in md


def test_buttons_and_forms():
    md = _render(_tree(_node(
        ['main-view'],
        buttons=[
            {'text': 'Delete', 'handlers': ['onDelete'], 'controller': 'main-view', 'toggles': '',
             'result': 'skipped (denylist / form submit)'},
            {'text': 'Echo', 'handlers': ['onEcho'], 'controller': 'main-view', 'toggles': '', 'result': 'clicked',
             'server_calls': [{'via': 'websocket', 'target': 'main_test.main_view', 'function': 'echo',
                               'args': ['a']}]},
        ],
        forms=[{'controller': 'main-view', 'action': '', 'method': 'post', 'submit_handlers': ['save'],
                'fields': [{'name': 'title', 'type': 'text', 'required': True, 'label': '', 'options': []}],
                'result': 'submitted by developer', 'navigates_to': '/~main-view~book'}],
    )))
    assert '"Delete" in `main-view` → `onDelete()` — skipped (denylist / form submit)' in md
    assert 'websocket call `main_test.main_view.echo(a)`' in md
    assert ('`title` (text, required); submit → `save()` — submitted by developer; '
            'navigates to `/~main-view~book`') in md


def test_merge_marks_login_required():
    anonymous = _tree(_node(['admin-only'], error_code=403))
    logged_in = _tree(_node(['admin-only'], seen_as='user admin'), _node(['secret'], seen_as='user admin'))
    tree = merge_crawls(anonymous, logged_in)
    md = _render(tree)
    assert '- **admin-only** — `/~admin-only` _(login required)_' in md
    assert '- **secret** — `/~secret` _(login required)_' in md


def test_models_section():
    md = render_skill(_tree(_node(['main-view'])), {
        'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01',
        'models': [{'name': 'Book', 'app': 'main_test', 'doc': 'A book.\n\nHas a title.'},
                   {'name': 'Author', 'app': 'main_test', 'doc': None}]})
    assert '## Data models' in md
    assert '### `Book` (main_test)\n\nA book.\n\nHas a title.\n' in md
    assert '### `Author` (main_test)\n\n_No documentation._' in md


def test_model_doc_ignores_generated_and_inherited_docstrings():
    from main_test.models import Book
    from sdc_core.management.commands.utils.teach_models import model_doc
    assert Book.__doc__  # set by Django / inherited from SdcModel
    assert model_doc(Book) == ast.get_docstring(_class_def(inspect.getfile(Book), 'Book'))


def test_add_class_docstring(tmp_path, monkeypatch):
    from sdc_core.management.commands.utils import teach_models
    src = tmp_path / 'models.py'
    src.write_text('import os\n\n\nclass Foo(object):\n    # comment\n    x = 1\n\n    def f(self):\n        pass\n')

    class Foo:
        pass

    monkeypatch.setattr(teach_models.inspect, 'getfile', lambda _: str(src))
    monkeypatch.setattr(teach_models.inspect, 'getsourcelines', lambda _: ([], 4))
    assert teach_models.model_doc(Foo) is None
    assert teach_models.add_class_docstring(Foo, 'A foo.\nSays """hi""".')
    assert src.read_text() == ('import os\n\n\nclass Foo(object):\n    """\n    A foo.\n    Says \\"\\"\\"hi\\"\\"\\".\n'
                               '    """\n    # comment\n    x = 1\n\n    def f(self):\n        pass\n')
    assert teach_models.model_doc(Foo) == 'A foo.\nSays """hi""".'
    assert not teach_models.add_class_docstring(Foo, 'again')  # already documented


def _class_def(file, name):
    with open(file) as f:
        return next(n for n in ast.walk(ast.parse(f.read())) if isinstance(n, ast.ClassDef) and n.name == name)


def test_model_socket_calls():
    tree = _tree(_node(
        ['book-list'],
        model_calls=[
            {'via': 'model-socket', 'controller': 'book-list', 'target': 'Book', 'function': 'connect',
             'query': ['author'], 'args': []},
            {'via': 'model-socket', 'controller': 'book-list', 'target': 'Book', 'function': 'load',
             'query': ['author'], 'args': []},
        ],
        buttons=[{'text': 'Save', 'handlers': ['onSave'], 'controller': 'book-list', 'toggles': '',
                  'result': 'clicked',
                  'server_calls': [{'via': 'model-socket', 'controller': 'book-list', 'target': 'Book',
                                    'function': 'save', 'query': [], 'args': ['data']}]}],
    ))
    tree['global']['model_calls'] = [{'via': 'model-socket', 'controller': 'nav-bar', 'target': 'SdcUser',
                                      'function': 'load', 'query': [], 'args': []}]
    md = _render(tree)
    assert '"Model socket (on load)"' in md
    assert ('  - Model socket (on load):\n    - `book-list`: `Book.connect()` filter `author`; '
            '`Book.load()` filter `author`') in md
    assert 'model-socket `Book.save(data)` from `book-list`' in md
    assert '## Global navigation (always visible)\n\n- Model socket (on load):\n  - `nav-bar`: `SdcUser.load()`' in md


def test_merge_keeps_global_model_calls():
    anonymous = _tree(_node(['main-view']))
    logged_in = _tree(_node(['main-view'], seen_as='user admin'))
    call = {'via': 'model-socket', 'controller': 'nav-bar', 'target': 'SdcUser', 'function': 'load',
            'query': [], 'args': []}
    logged_in['global']['model_calls'] = [call]
    assert merge_crawls(anonymous, logged_in)['global']['model_calls'] == [call]


def test_controller_docs_section():
    md = render_skill(_tree(_node(['main-view']), _node(['main-view', 'book-edit'])), {
        'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01',
        'controller_infos': {'main-view': {'app': 'main_test', 'view_class': 'main_test.sdc_views.MainView',
                                           'url': '/sdc_view/main_test/main_view', 'doc': 'Start page.\n\nLists books.'},
                             'book-edit': {'app': 'main_test', 'doc': None}}})
    assert ('### `<main-view>`\n\nStart page.\n\nLists books.\n\n_app `main_test`, server view '
            '`main_test.sdc_views.MainView`, Django URL `/sdc_view/main_test/main_view`_\n') in md
    assert '### `<book-edit>`\n\n_No documentation._\n' in md


def test_controller_jsdoc(tmp_path):
    from sdc_core.management.commands.utils.teach_controllers import add_controller_doc, controller_doc
    js = tmp_path / 'book_edit.js'
    head = ("import {AbstractSDC, app} from 'sdc_client';\n\n"
            "/**\n * Helper, not the controller doc\n */\nconst x = 1;\n\n")
    body = "class BookEditController extends AbstractSDC {\n}\n\napp.register(BookEditController);\n"
    js.write_text(head + body)
    assert controller_doc(str(js), 'book-edit') is None
    assert add_controller_doc(str(js), 'book-edit', 'Edits a book.\n\nEnds a comment */ safely.')
    assert js.read_text() == head + ('/**\n * Edits a book.\n *\n * Ends a comment *\\/ safely.\n */\n' + body)
    assert controller_doc(str(js), 'book-edit') == 'Edits a book.\n\nEnds a comment *\\/ safely.'
    assert not add_controller_doc(str(js), 'book-edit', 'again')  # already documented


def test_controller_jsdoc_exported_and_fallback(tmp_path):
    from sdc_core.management.commands.utils.teach_controllers import controller_doc
    js = tmp_path / 'nav.js'
    js.write_text("/**\n   * Navigates.\n   *   indented\n   */\nexport class OtherNameController extends AbstractSDC {}\n")
    assert controller_doc(str(js), 'sdc-navigator') == 'Navigates.\n  indented'


def test_prepare_teaching():
    import io
    from django.core.management import call_command

    def run(*args):
        out = io.StringIO()
        call_command('sdc_prepare_teaching', *args, stdout=out)
        return out.getvalue()

    # Every model and controller of the test project is documented
    text = run()
    assert text.startswith('# Prepare this SimpleDomControl project for `sdc_teach`')
    assert text.rstrip().endswith('Nothing to do: every SDC model and controller of the project is documented.')
    text = run('--all')
    assert '## All models and controllers' in text
    assert '- Model `Book` (main_test): main_test/models.py:' in text
    assert ('- Controller `<error404>` (main_test): '
            'main_test/Assets/src/main_test/controller/error_404/error_404.js:') in text
    assert '  Current documentation:\n  > ' in text


def test_app_skill():
    from sdc_core.management.commands.utils.teach_markdown import render_app_skill
    md = render_app_skill('main_test', {
        'book-edit': {'app': 'main_test', 'view_class': 'main_test.sdc_views.BookEdit',
                      'url': '/sdc_view/main_test/book_edit/<int:pk>', 'doc': 'Edits a `Book`.'},
        'admin-only': {'app': 'main_test', 'doc': None},
    }, [{'name': 'Book', 'app': 'main_test', 'doc': 'A book.',
         'fields': [{'name': 'title', 'type': 'CharField', 'related': None},
                    {'name': 'author', 'type': 'ForeignKey', 'related': 'Author'}]}],
        {'project': 'Demo', 'date': '2026-01-01'})
    assert md.startswith('---\nname: main-test\n')
    assert '## Navigation tree' not in md
    assert md.index('### `<admin-only>`') < md.index('### `<book-edit>`')
    assert ('### `<book-edit>`\n\nEdits a `Book`.\n\n_server view `main_test.sdc_views.BookEdit`, Django URL '
            '`/sdc_view/main_test/book_edit/<int:pk>`, required URL params `pk`_\n') in md
    assert '### `<admin-only>`\n\n_No documentation._\n' in md
    assert '### `Book`\n\nA book.\n\nFields: `title` (CharField), `author` → `Author`\n' in md


def test_model_fields_respect_sdc_meta():
    from sdc_core.management.commands.utils.teach_models import sdc_models
    fields = {m['name']: [f['name'] for f in m['fields']] for m in sdc_models()}
    assert 'password' not in fields['SdcUser']
    assert fields['Book'] == ['id', 'title', 'author']
