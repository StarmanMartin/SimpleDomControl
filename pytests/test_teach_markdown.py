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


def test_views_and_args():
    md = _render(_tree(
        _node(['main-view'], {'1.tab': 'books'}),
        _node(['main-view', 'book-edit'], {'1.tab': 'books', '2.pk': 3, '2.edit': True}),
    ))
    assert md.startswith('---\nname: demo-ui\n')
    assert '### `<main-view>` — `/~main-view`' in md
    assert '### `<book-edit>` — `/~main-view~book-edit`' in md
    # Arguments of the view itself, without the depth prefix; the parent's tab stays with the parent
    assert '- Arguments: `edit` (bool, e.g. `True`); `pk` (number, e.g. `3`)' in md
    assert '- Arguments: `tab` (string, e.g. `books`)' in md


def test_one_entry_per_view():
    login = dict(links=[{'text': 'Register', 'target': {'href': '/~register'}, 'only_logged_in': False,
                          'only_logged_out': False}])
    md = _render(_tree(
        _node(['sdc-login'], **login),
        _node(['editor', 'sdc-login'], {'2.next': '~editor'}, **login),
        _node(['other', 'sdc-login'], {'2.next': '~other'}, **login),
    ))
    assert md.count('### `<sdc-login>`') == 1
    assert '- Also at: `/~editor~sdc-login`, `/~other~sdc-login`' in md
    assert '- Arguments: `next` (string, e.g. `~editor`, `~other`)' in md
    assert md.count('"Register" → `/~register`') == 1


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
    assert '### `<admin-only>` — `/~admin-only` _(login required)_' in md
    assert '### `<secret>` — `/~secret` _(login required)_' in md


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
    assert ('- Model socket (on load):\n  - `book-list`: `Book.connect()` filter `author`; '
            '`Book.load()` filter `author`') in md
    assert 'model-socket `Book.save(data)` from `book-list`' in md
    assert '## Global navigation (always visible)\n\n- Model socket (on load):\n  - `nav-bar`: `SdcUser.load()`' in md
    # The assistant profile leaves the socket traffic out
    from sdc_core.management.commands.utils.teach_markdown import render_skill as render
    assistant = render(tree, {'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01'},
                       audience='assistant')
    assert 'Model socket' not in assistant and 'Book.save' not in assistant


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
    assert ('### `<main-view>` — `/~main-view`\n\nStart page.\n\nLists books.\n\n_app `main_test`, server view '
            '`main_test.sdc_views.MainView`, Django URL `/sdc_view/main_test/main_view`_\n') in md
    assert '### `<book-edit>` — `/~main-view~book-edit`\n\n_No documentation._\n' in md
    # The documentation is part of the view's entry: no separate controller section for views
    assert '## Controllers\n' not in md


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
    assert text.rstrip().endswith(
        'Nothing to do: every SDC model, controller and button action of the project is documented.')
    text = run('--all')
    assert '## All models and controllers' in text
    assert '- Model `Book` (main_test): main_test/models.py:' in text
    assert ('- Controller `<error404>` (main_test): '
            'main_test/Assets/src/main_test/controller/error_404/error_404.js:') in text
    assert '  Current documentation:\n  > ' in text
    assert '## All button actions' in text
    assert ('- Button action `add_x()` of `<book-edit>` (main_test): '
            'main_test/Assets/src/main_test/controller/book_edit/book_edit.js:') in text


def test_app_skill_json(tmp_path):
    from types import SimpleNamespace
    from sdc_core.management.commands.utils.teach_apps import app_skill_data, load_app_skills, write_app_skill
    data = app_skill_data('main_test', {
        'book-edit': {'app': 'main_test', 'view_class': 'main_test.sdc_views.BookEdit',
                      'url': '/sdc_view/main_test/book_edit/<int:pk>', 'doc': 'Edits a `Book`.', 'file': '/abs/x.js'},
        'admin-only': {'app': 'main_test', 'doc': None},
    }, [{'name': 'Book', 'app': 'main_test', 'doc': 'A book.', 'model': object,
         'fields': [{'name': 'author', 'type': 'ForeignKey', 'related': 'Author'}]}])
    assert list(data['controllers']) == ['admin-only', 'book-edit']
    assert data['controllers']['book-edit'] == {'doc': 'Edits a `Book`.', 'view_class': 'main_test.sdc_views.BookEdit',
                                                'url': '/sdc_view/main_test/book_edit/<int:pk>', 'url_params': ['pk'],
                                                'actions': {}}
    assert data['models'] == {'Book': {'doc': 'A book.',
                                       'fields': [{'name': 'author', 'type': 'ForeignKey', 'related': 'Author'}]}}
    write_app_skill(str(tmp_path), data)
    (tmp_path / 'broken').mkdir()
    (tmp_path / 'broken' / 'SDC_SKILL.json').write_text('{not json')
    configs = [SimpleNamespace(path=str(tmp_path), label='main_test'),
               SimpleNamespace(path=str(tmp_path / 'broken'), label='broken'),
               SimpleNamespace(path=str(tmp_path / 'missing'), label='missing')]
    assert load_app_skills(configs) == {'main_test': data}


def test_apply_app_skills():
    from sdc_core.management.commands.utils.teach_apps import apply_app_skills
    skills = {'main_test': {'models': {'Book': {'doc': 'json book'}},
                            'controllers': {'book-edit': {'doc': 'json edit'}, 'admin-only': {'doc': None}}}}

    def items():
        return ([{'name': 'Book', 'app': 'main_test', 'doc': 'code book'}, {'name': 'Author', 'app': 'main_test', 'doc': None}],
                {'book-edit': {'app': 'main_test', 'doc': None}, 'admin-only': {'app': 'main_test', 'doc': 'code admin'}})

    models, controllers = items()
    apply_app_skills(models, controllers, skills, prefer_json=True)
    assert [m['doc'] for m in models] == ['json book', None]
    assert controllers == {'book-edit': {'app': 'main_test', 'doc': 'json edit'},
                           'admin-only': {'app': 'main_test', 'doc': 'code admin'}}
    models, controllers = items()
    apply_app_skills(models, controllers, skills, prefer_json=False)
    assert models[0]['doc'] == 'code book'
    assert controllers['book-edit']['doc'] == 'json edit'


def test_model_fields_respect_sdc_meta():
    from sdc_core.management.commands.utils.teach_models import sdc_models
    fields = {m['name']: [f['name'] for f in m['fields']] for m in sdc_models()}
    assert 'password' not in fields['SdcUser']
    assert fields['Book'] == ['id', 'title', 'author']


def test_unreached_controllers_are_documented():
    md = render_skill(_tree(_node(['main-view'])), {
        'project': 'Demo', 'crawled_as': ['user admin'], 'date': '2026-01-01',
        'controller_infos': {'main-view': {'app': 'main_test', 'doc': 'Start page.'},
                             'book-edit': {'app': 'main_test', 'url': '/sdc_view/main_test/book_edit/<int:pk>',
                                           'doc': 'Edits a book.'}}})
    reached, unreached = md.split('## Controllers not reached by the crawl')
    assert '### `<main-view>`' in reached and '<book-edit>' not in reached
    assert ('### `<book-edit>`\n\nEdits a book.\n\n_app `main_test`, Django URL '
            '`/sdc_view/main_test/book_edit/<int:pk>`, required URL params `pk`_\n') in unreached
    assert '<main-view>' not in unreached


def test_no_unreached_section_when_all_controllers_were_seen():
    md = render_skill(_tree(_node(['main-view'])), {
        'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01',
        'controller_infos': {'main-view': {'app': 'main_test', 'doc': 'Start page.'}}})
    assert 'not reached by the crawl' not in md


def test_url_guide_is_part_of_the_skill_file():
    from sdc_core.management.commands.utils.teach_markdown import SDC_URL_GUIDE
    md = _render(_tree(_node(['main-view'])))
    assert SDC_URL_GUIDE in md
    assert md.index('## How to read SDC URLs') < md.index('## How to operate this app')
    assert '`N.key` belongs to the view at depth `N`' in SDC_URL_GUIDE


def test_button_actions_are_documented():
    infos = {'main-view': {'app': 'main_test', 'doc': 'Start page.',
                           'actions': {'onDelete': 'Deletes the book.\n\nCannot be undone.', 'onEcho': None}}}
    md = render_skill(_tree(_node(['main-view'], buttons=[
        {'text': 'Delete', 'handlers': ['onDelete'], 'controller': 'main-view', 'toggles': '',
         'result': 'skipped (denylist / form submit)'},
        {'text': 'Echo', 'handlers': ['onEcho'], 'controller': 'main-view', 'toggles': '', 'result': 'clicked'},
    ])), {'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01', 'controller_infos': infos})
    assert ('"Delete" in `main-view` → `onDelete()` — skipped (denylist / form submit) — '
            'action: `onDelete()`: Deletes the book.') in md
    assert '"Echo" in `main-view` → `onEcho()` — clicked\n' in md
    assert ('Button actions (`sdc_click` handlers):\n- `onDelete()`: Deletes the book.\n'
            '- `onEcho()`: _No documentation._\n') in md


def test_controller_actions_from_template_and_code(tmp_path):
    from sdc_core.management.commands.utils.teach_controllers import (click_handlers, controller_actions,
                                                                       method_doc, method_line)
    own = tmp_path / 'book_list.js'
    own.write_text("class BookListController extends AbstractSDC {\n"
                   "    /**\n     * Opens the next page.\n     * @param {jQuery} $btn\n     */\n"
                   "    async next($btn) {}\n\n"
                   "    render() { return '<button sdc_click=\\\"reload\\\">R</button>'; }\n"
                   "    reload() {}\n"
                   "    removeInstance($btn) {}\n}\n")
    other = tmp_path / 'other.js'
    other.write_text("class X extends AbstractSDC {\n  /** Reloads the list. */\n  reload() {}\n}\n")
    assert click_handlers('<a sdc_click="next  this.event_x">', '<b sdc_click=\'next\'>') == ['next']
    assert method_doc(own.read_text(), 'next') == 'Opens the next page.'
    assert method_doc(own.read_text(), 'reload') is None
    assert method_line(str(own), 'reload') == 9
    infos = {'book-list': {'file': str(own), 'view_class': 'missing.View'},
             'other': {'file': str(other), 'view_class': ''}}
    # "next" comes from the template of the server view, here: a template handler defined by the class
    controller_actions(infos, template_handlers=['next', 'removeInstance', 'unknown'])
    assert infos['book-list']['actions'] == {'reload': 'Reloads the list.', 'next': 'Opens the next page.',
                                             'removeInstance': None}
    assert infos['other']['actions'] == {}


def test_controller_actions_of_the_test_project():
    from sdc_core.management.commands.utils.teach_controllers import sdc_controllers
    infos = sdc_controllers()
    assert infos['book-edit']['actions'] == {
        'add_x': 'Appends " X" to the book title in the form and sets the author to the record with id 1; nothing '
                 'is saved\nuntil the form is saved.'}
    assert infos['sdc-list-view']['actions']['removeInstance'].startswith('Deletes the record')


def test_apply_app_skills_actions():
    from sdc_core.management.commands.utils.teach_apps import apply_app_skills
    skills = {'main_test': {'controllers': {'book-edit': {'doc': None, 'actions': {'add_x': 'json', 'save': None}}}}}
    controllers = {'book-edit': {'app': 'main_test', 'doc': 'x', 'actions': {'add_x': 'code', 'other': None}}}
    apply_app_skills([], controllers, skills, prefer_json=False)
    assert controllers['book-edit']['actions'] == {'add_x': 'code', 'other': None}
    apply_app_skills([], controllers, skills, prefer_json=True)
    assert controllers['book-edit']['actions'] == {'add_x': 'json', 'other': None}


def test_skill_data_is_json_and_lists_embedded_controllers():
    import json
    from sdc_core.management.commands.utils.teach_data import FORMAT, build_skill_data
    from sdc_core.management.commands.utils.teach_markdown import render_markdown
    node = _node(['main-view'], seen_as='user admin',
                 controllers=[{'tag': 'main-view', 'url_params': [], 'parent': None, 'nav_idx': 0},
                              {'tag': 'sdc-search-view', 'url_params': [], 'parent': 'main-view', 'nav_idx': 0}])
    infos = {'main-view': {'app': 'main_test', 'doc': 'Start page.', 'actions': {'go': 'Goes.'}},
             'sdc-search-view': {'app': 'sdc_tools', 'doc': 'Search bar.'},
             'book-edit': {'app': 'main_test', 'doc': 'Edits a book.'}}
    data = build_skill_data(_tree(node), {'project': 'Demo', 'crawled_as': ['user admin'], 'date': '2026-01-01',
                                          'logged_in_label': 'user admin', 'controller_infos': infos})
    assert json.loads(json.dumps(data))['format'] == FORMAT
    assert [v['tag'] for v in data['views']] == ['main-view']
    assert data['views'][0]['embedded'] == ['sdc-search-view'] and data['views'][0]['requires_login']
    assert [c['tag'] for c in data['embedded']] == ['sdc-search-view']
    assert [c['tag'] for c in data['unreached']] == ['book-edit']
    md = render_markdown(data)
    assert '## Embedded controllers\n\nControllers shown inside the views above (or globally).\n\n' \
           '### `<sdc-search-view>`\n\nSearch bar.' in md
    assert 'Button actions (`sdc_click` handlers):\n- `go()`: Goes.' in md


def test_skill_file_of_the_test_project_stays_small():
    """Size budget (about 4 characters per token): the documentation of the test project's apps alone."""
    from sdc_core.management.commands.sdc_teach import Command
    from sdc_core.management.commands.utils.teach_controllers import sdc_controllers
    from sdc_core.management.commands.utils.teach_models import sdc_models
    meta = {'project': 'SdcTest', 'crawled_as': ['anonymous'], 'controller_infos': sdc_controllers(),
            'models': sdc_models(), 'date': '2026-01-01'}
    tree = {'nodes': {}, 'errors': [], 'global': {}}
    assert Command.tokens(render_skill(tree, meta)) < 8000
    assert Command.tokens(render_skill(tree, meta, audience='assistant')) < 7000
    assert Command.data_file('/x/SDC_SKILL.md') == '/x/SDC_SKILL.data.json'


def test_ai_tags_of_controllers(tmp_path):
    from sdc_core.management.commands.utils.teach_controllers import (controller_ai_tags, controller_doc,
                                                                       split_ai_tags, sdc_controllers)
    assert split_ai_tags('Nav frame.\n\n@ai-hidden\n@ai-summary  Owns the URL.') == (
        'Nav frame.', {'hidden': True, 'summary': 'Owns the URL.', 'tasks': []})
    assert split_ai_tags(None) == (None, {'hidden': False, 'summary': None, 'tasks': []})
    # A recipe: the lines after @ai-task up to a blank line
    assert split_ai_tags('Form.\n\n@ai-task Register a user\n1. Open `/~register`.\n- Fill it.\n\nMore text.') == (
        'Form.\n\n\nMore text.', {'hidden': False, 'summary': None,
                                   'tasks': [{'title': 'Register a user', 'steps': ['Open `/~register`.', 'Fill it.']}]})
    js = tmp_path / 'x.js'
    js.write_text('/**\n * Helper.\n *\n * @ai-hidden\n */\nclass XController extends AbstractSDC {}\n')
    assert controller_doc(str(js), 'x') == 'Helper.'
    assert controller_ai_tags(str(js), 'x') == {'hidden': True, 'summary': None, 'tasks': []}
    infos = sdc_controllers()
    assert infos['sdc-navigator']['hidden'] and not infos['sdc-list-view']['hidden']
    assert infos['sdc-search-view']['summary'].startswith('Search and paging bar')
    assert '@ai-' not in infos['sdc-navigator']['doc']


def test_assistant_profile_leaves_out_hidden_controllers():
    from sdc_core.management.commands.sdc_teach import Command
    infos = {'main-view': {'app': 'main_test', 'doc': 'Start.'},
             'sdc-navigator': {'app': 'sdc_tools', 'doc': 'Nav.', 'hidden': True},
             'sdc-user': {'app': 'sdc_user', 'doc': 'User.', 'hidden': True}}
    meta = {'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01', 'controller_infos': infos}
    node = _node(['main-view'], controllers=[{'tag': 'main-view', 'url_params': [], 'parent': None, 'nav_idx': 0},
                                             {'tag': 'sdc-navigator', 'url_params': [], 'parent': None,
                                              'nav_idx': None}])
    agent, assistant = render_skill(_tree(node), meta), render_skill(_tree(node), meta, audience='assistant')
    assert '<sdc-navigator>' in agent and '<sdc-user>' in agent
    assert '<sdc-navigator>' not in assistant and '<sdc-user>' not in assistant and '<main-view>' in assistant
    assert 'A view is ready when' in agent and 'A view is ready when' not in assistant
    assert Command.skill_files('/p/SDC_SKILL.md') == [('agent', '/p/SDC_SKILL.md'),
                                                      ('assistant', '/p/SDC_SKILL.assistant.md')]
    assert Command.skill_files('/p/SDC_SKILL.md', 'assistant') == [('assistant', '/p/SDC_SKILL.assistant.md')]


def test_merge_of_several_roles_records_who_may_open_a_view():
    from sdc_core.management.commands.utils.teach_data import build_skill_data
    anonymous = _tree(_node(['staff-only'], error_code=403), _node(['main-view']))
    editor = _tree(_node(['staff-only'], seen_as='editor', error_code=403), _node(['main-view'], seen_as='editor'))
    admin = _tree(_node(['staff-only'], seen_as='admin'), _node(['main-view'], seen_as='admin'))
    tree = merge_crawls(merge_crawls(anonymous, editor), admin)
    data = build_skill_data(tree, {'project': 'Demo', 'crawled_as': ['anonymous', 'editor', 'admin'],
                                   'date': '2026-01-01', 'logged_in_label': 'admin'})
    views = {v['tag']: v for v in data['views']}
    assert views['staff-only']['available_to'] == ['admin']
    assert views['staff-only']['denied'] == ['anonymous', 'editor'] and views['staff-only']['requires_login']
    assert views['main-view']['available_to'] == ['admin', 'anonymous', 'editor'] and not views['main-view']['denied']
    md = render_markdown_of(data)
    assert '### `<staff-only>` — `/~staff-only` _(login required; available to admin)_' in md
    assert '### `<main-view>` — `/~main-view`\n' in md


def render_markdown_of(data, audience='agent'):
    from sdc_core.management.commands.utils.teach_markdown import render_markdown
    return render_markdown(data, audience)


def test_model_routes_and_recipes():
    from sdc_core.management.commands.utils.teach_data import build_skill_data, model_routes, route_paths
    infos = {'sdc-list-view': {}, 'sdc-detail-view': {}, 'sdc-model-form': {},
             'register': {'app': 'sdc_user', 'doc': 'Sign up.',
                          'tasks': [{'title': 'Register', 'steps': ['Open `/~register`.', 'Fill the form.']}]}}
    author = {'name': 'Author', 'app': 'main_test', 'doc': 'An author.',
              'views': {'list': True, 'detail': True, 'create': True, 'edit': True, 'remove': True}}
    content = {'name': 'Content', 'app': 'main_test', 'views': {'create': True, 'edit': True}}
    assert model_routes(author, infos) == {'list': '/~sdc-list-view~&model=Author',
                                           'detail': '/~sdc-detail-view~&model=Author&pk=<id>',
                                           'create': '/~sdc-model-form~&model=Author',
                                           'edit': '/~sdc-model-form~&model=Author&pk=<id>'}
    assert model_routes(author, {}) == {}
    # Routes with <id> need a record; Content has none
    assert route_paths([author, content], infos, {'Author': 3}) == [
        '/~sdc-list-view~&model=Author', '/~sdc-detail-view~&model=Author&pk=3', '/~sdc-model-form~&model=Author',
        '/~sdc-model-form~&model=Author&pk=3', '/~sdc-model-form~&model=Content']
    tree = _tree(_node(['main-view']))
    tree['visits'] = {'/~sdc-list-view~&model=Author': {'anonymous': None, 'editor': None},
                      '/~sdc-detail-view~&model=Author&pk=3': {'anonymous': 403}}
    data = build_skill_data(tree, {'project': 'Demo', 'crawled_as': ['anonymous', 'editor'], 'date': '2026-01-01',
                                   'controller_infos': infos, 'models': [author]})
    routes = data['models'][0]['routes']
    assert routes['list'] == {'path': '/~sdc-list-view~&model=Author', 'ok': ['anonymous', 'editor'], 'denied': []}
    assert routes['detail']['denied'] == ['anonymous'] and routes['create']['ok'] == []
    md = render_markdown_of(data, 'assistant')
    assert '## Common tasks\n\n- Find a record:' in md
    assert ('- `Author`: list `/~sdc-list-view~&model=Author` (opens for every crawled role); detail '
            '`/~sdc-detail-view~&model=Author&pk=<id>` (error view for anonymous); create '
            '`/~sdc-model-form~&model=Author` (not verified)') in md
    assert 'delete: "Remove" in its list' in md
    assert '### Register (`<register>`)\n\n1. Open `/~register`.\n2. Fill the form.\n' in md


def test_index_and_describe_of_models_and_controllers():
    from sdc_core.management.commands.utils.teach_data import build_skill_data
    from sdc_core.management.commands.utils.teach_markdown import describe, render_index
    infos = {'sdc-list-view': {'app': 'sdc_tools', 'doc': 'Generic list. Shows records.'},
             'sdc-model-form': {'app': 'sdc_tools', 'doc': 'Form.', 'summary': 'Create/edit form of a record.'}}
    author = {'name': 'Author', 'app': 'main_test', 'doc': 'An author.\n\nMore.', 'views': {'list': True},
              'fields': [{'name': 'name', 'type': 'CharField', 'related': None}]}
    data = build_skill_data(_tree(), {'project': 'Demo', 'crawled_as': ['anonymous'], 'date': '2026-01-01',
                                      'controller_infos': infos, 'models': [author]})
    index = render_index(data)
    assert '- `sdc-list-view` — Generic list.' in index
    assert '- `sdc-model-form` — Create/edit form of a record.' in index
    assert '- `Author` — An author. Fields: name.' in index
    text = describe(data, 'author')
    assert text.startswith('### `Author` (main_test)') and 'Views: list `/~sdc-list-view~&model=Author`' in text
    assert describe(data, '<sdc-list-view>').startswith('_No crawled link opened this view')
