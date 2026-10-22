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
