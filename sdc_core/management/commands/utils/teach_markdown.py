"""
Renders the skill data of ``teach_data.build_skill_data`` (the crawl of ``teach_crawler.Crawler`` plus the
documentation) as a Markdown skill file for AI agents.
"""
from sdc_core.management.commands.utils.teach_data import build_skill_data, url_params  # noqa: F401 (re-export)


SDC_URL_GUIDE_HEADING = '## How to read SDC URLs'
# The rules of the sdc-navigator (``_prepareUrl`` / ``_handleUrl`` in sdc_navigator.js); part of every skill file and,
# without one, of the AI assistant's system prompt
SDC_URL_GUIDE = SDC_URL_GUIDE_HEADING + """

The app is a single page: the `sdc-navigator` shows nested views (SDC controllers) and the URL lists them.

- `/~parent-view~child-view~&key=value&other=2`: one controller tag per `~` segment, outermost first; every view is \
rendered inside the previous one. The part before the first `~` (usually `/`) is the Django page.
- The arguments start at the first `&` (or `?`): `key=value` pairs joined by `&`. Values are URL-decoded; numbers and \
`true`/`false` become numbers and booleans.
- A plain key belongs to the deepest view of the path. `N.key` belongs to the view at depth `N` (1 = first view): \
`/~book-list~book-edit~&1.page=2&pk=3` gives `page=2` to `book-list` and `pk=3` to `book-edit`. A view receives its \
arguments as `this.params` (`data-*` attributes; `camelCase` keys become `kebab-case`). The links of the current URL \
show the arguments with their depth (`2.pk=3`).
- Navigating keeps the arguments of the views above the opened view; the opened view gets only the arguments given.
- Relative paths are resolved against the current URL: `.` = the current path, `..` = one view up, `*` = keep the \
view at this depth, `..~other-view` replaces the deepest view, `.~child-view~&pk=3` opens a view below the current \
one. A path that does not start with `/`, `~`, `.` or `*` also opens below the current view (`book-edit` = \
`.~book-edit`).
- An empty path (`/`) opens the navigator's default controller; a view may open a default child view by itself.
- An unknown tag shows `sdc-error 404`; a view the user may not open shows `sdc-error 403`.
- `window.sdcNav.goTo(path, {key: value})`, the `goTo` event and links with the class `navigation-links` navigate \
without reloading the page (the AI assistant's `navigate` and `click` do the same). Opening the URL directly loads \
the whole page."""



# Operating rules for every reader of the skill file
RULES = [
    'Each view below is listed once, with the paths it was seen at; its links are resolved by the `sdc-navigator` '
    '(absolute paths with the arguments of their view depth).',
    'Buttons call controller methods named in their `sdc_click` attribute; "action:" is what the method does (its '
    'JSDoc), the text after the arrow is what the crawler observed when it clicked the button.',
    'Buttons marked "skipped" were not clicked by the crawler because they look destructive (delete, logout, save, '
    'submit); confirm with the user before clicking them.',
    'Forms were not submitted automatically: "submitted by developer" shows what a manual submit did, "not '
    'submitted" means the outcome is unknown.',
    'A view showing `sdc-error 403` needs a logged-in user with the right permissions.',
]
# Additional rules for coding agents that drive a browser themselves
AGENT_RULES = [
    'A view is ready when `window.sdcNav && !window.sdcNav._is_processing` and no '
    '`.sdc_sub_detail_container.loading` element exists.',
    'Server calls (`this.serverCall(...)`) execute methods of the matching `SDCView` on the server.',
    'All SdcModel WebSocket traffic (`/sdc_ws/model/<Model>`) was recorded per controller: "Model socket (on '
    'load)" lists what each controller requests when the view opens, buttons and forms list what they trigger, as '
    '`Model.event(args)` with the `model_query` filter keys. `connect` subscribes to live updates of the filtered '
    'rows; `load`, `save`, `create`, `delete`, ... read or write data.',
]


def _type_of(values):
    types = set()
    for v in values:
        if isinstance(v, bool):
            types.add('bool')
        elif isinstance(v, (int, float)):
            types.add('number')
        elif isinstance(v, dict):
            types.add('object')
        else:
            types.add('string')
    return '|'.join(sorted(types)) or 'string'


def _code(v):
    return f'`{v}`'


def _model_call(call):
    query = f' filter {", ".join(map(_code, call["query"]))}' if call.get('query') else ''
    return f'`{call["target"]}.{call["function"]}({", ".join(call["args"])})`{query}'


def _call_text(call):
    if call['via'] == 'model-socket':
        source = f' from {_code(call["controller"])}' if call.get('controller') else ''
        return f'model-socket {_model_call(call)}{source}'
    return f'{call["via"]} call `{call["target"]}.{call["function"]}({", ".join(call["args"])})`'


def _effects(b, agent=True):
    """Describes the observed outcome of a clicked button or a submitted form."""
    effect = [b.get('result', '')]
    if b.get('navigates_to'):
        effect.append(f'navigates to {_code(b["navigates_to"])}')
    if b.get('opens'):
        effect.append('shows ' + ', '.join(map(_code, b['opens'])))
    if b.get('updates'):
        effect.append('updates view: ' + ', '.join(f'"{t}"' for t in b['updates']))
    if b.get('controller_count') and agent:
        effect.append('controllers {} → {}'.format(*b['controller_count']))
    if b.get('modal'):
        effect.append('opens a modal')
    if b.get('toggles'):
        effect.append(f'bootstrap toggle `{b["toggles"]}`')
    for call in b.get('server_calls', []) if agent else []:
        effect.append(_call_text(call))
    for alert in b.get('alerts', []):
        effect.append(f'alert "{alert}"')
    for dialog in b.get('dialogs', []):
        effect.append(f'dialog "{dialog}"')
    return '; '.join(filter(None, effect))


def _summary(doc):
    """The first paragraph of a doc comment on one line."""
    return ' '.join((doc or '').strip().split('\n\n')[0].split())


def _actions_of(data):
    """``{controller tag: {handler: doc}}`` of all views and controllers in the skill data."""
    actions = {}
    for item in data['views'] + data['embedded'] + data['unreached']:
        actions[item['tag']] = item.get('actions') or {}
    return actions


def _action_docs(button, actions):
    """The documented actions (JSDoc of the ``sdc_click`` handlers) of a button."""
    docs = actions.get(button.get('controller')) or {}
    return [f'`{h}()`: {_summary(docs[h])}' for h in button['handlers'] if docs.get(h)]


def _button_line(b, actions, agent):
    handler = ', '.join(f'`{h}()`' for h in b['handlers'])
    if not handler and agent:
        handler = 'no sdc_click handler'
    where = f' in {_code(b["controller"])}' if b.get('controller') else ''
    docs = _action_docs(b, actions)
    return (f'"{b["text"] or "(no label)"}"{where}' + (f' → {handler}' if handler else '') + f' — {_effects(b, agent)}'
            + (f' — action: {"; ".join(docs)}' if docs else ''))


def _form_line(f, agent):
    fields = ', '.join(
        f'{_code(x["name"])} ({x["type"]}{", required" if x["required"] else ""}'
        f'{", options: " + "/".join(x["options"]) if x["options"] else ""})'
        for x in f['fields']) or 'no visible fields'
    submit = ''
    if f['submit_handlers'] and agent:
        submit = f'; submit → {", ".join(f"`{h}()`" for h in f["submit_handlers"])}'
    outcome = f' — {_effects(f, agent)}' if f.get('result') else ''
    return f'in {_code(f["controller"])}: {fields}{submit}{outcome}'


def _link_line(l):
    flags = ' _(logged in only)_' if l.get('only_logged_in') else (
        ' _(logged out only)_' if l.get('only_logged_out') else '')
    return f'"{l["text"]}" → {_code(l["target"]["href"])}{flags}'


def _render_items(title, items, pad, lines):
    if items:
        lines.append(f'{pad}- {title}:')
        lines += [f'{pad}  - {i}' for i in items]


def _render_model_calls(calls, pad, lines):
    by_controller = {}
    for call in calls:
        by_controller.setdefault(call['controller'] or '?', []).append(call)
    for controller, calls in sorted(by_controller.items()):
        lines.append(f'{pad}- {_code(controller)}: ' + '; '.join(map(_model_call, calls)))


def _source_line(item, show_app=True):
    params = item.get('url_params') or []
    source = [f'app `{item["app"]}`' if show_app and item.get('app') else '',
              f'server view {_code(item["view_class"])}' if item.get('view_class') else '',
              f'Django URL {_code(item["url"])}' if item.get('url') else '',
              f'required URL params {", ".join(map(_code, params))}' if params else '']
    return '_' + ', '.join(filter(None, source)) + '_' if any(source) else ''


def _render_actions(actions, lines):
    """What the controller's buttons do: the JSDoc of every ``sdc_click`` handler of its template and code."""
    if not actions:
        return
    lines.append('Button actions (`sdc_click` handlers):')
    for handler, doc in sorted(actions.items()):
        lines.append(f'- `{handler}()`: ' + (_summary(doc) if doc else '_No documentation._'))
    lines.append('')


def _render_view(view, actions, lines, agent):
    flags = []
    if view['requires_login']:
        flags.append('login required')
    for error in view['errors']:
        flags.append(f'shows sdc-error {error["code"]} for {", ".join(error["seen_as"])}')
    title = ' / '.join(view['headings'])
    lines.append(f'### `<{view["tag"]}>` — {_code(view["href"])}' + (f' — "{title}"' if title else '')
                 + (f' _({"; ".join(flags)})_' if flags else ''))
    lines.append('')
    lines += [view['doc'].strip() if view.get('doc') else '_No documentation._', '']
    facts = []
    if len(view['paths']) > 1:
        facts.append('- Also at: ' + ', '.join(map(_code, view['paths'][1:])))
    if view['url_params']:
        facts.append(f'- Required URL params: {", ".join(map(_code, view["url_params"]))}')
    if view['args']:
        facts.append('- Arguments: ' + '; '.join(
            f'{_code(k)} ({_type_of(v)}, e.g. {", ".join(_code(x) for x in v[:3])})'
            for k, v in sorted(view['args'].items())))
    if view['embedded']:
        facts.append(f'- Embedded controllers: {", ".join(map(_code, view["embedded"]))}')
    _render_items('Links', [_link_line(l) for l in view['links']], '', facts)
    _render_items('Buttons', [_button_line(b, actions, agent) for b in view['buttons']], '', facts)
    _render_items('Forms', [_form_line(f, agent) for f in view['forms']], '', facts)
    if view['model_calls'] and agent:
        facts.append('- Model socket (on load):')
        _render_model_calls(view['model_calls'], '  ', facts)
    external = sorted({e['href'] for e in view['external']})
    if external:
        facts.append(f'- Non-SDC links: {", ".join(map(_code, external))}')
    if facts:
        lines += facts + ['']
    source = _source_line(view, show_app=True) if agent else ''
    if source:
        lines += [source, '']
    _render_actions(view.get('actions'), lines)


def _render_controllers(items, lines, heading, intro=None, agent=True):
    if not items:
        return
    lines += [heading, '']
    if intro:
        lines += [intro, '']
    for item in items:
        lines += [f'### `<{item["tag"]}>`', '', item['doc'].strip() if item.get('doc') else '_No documentation._', '']
        source = _source_line(item) if agent else ''
        if source:
            lines += [source, '']
        _render_actions(item.get('actions'), lines)


def _render_models(models, lines, show_app=True):
    if not models:
        return
    lines += ['## Data models', '',
              'SDC models are loaded and saved over the model WebSocket '
              '(`this.querySet("Name", {filter})` in a controller).', '']
    for m in models:
        lines += [f'### `{m["name"]}`' + (f' ({m["app"]})' if show_app else ''), '',
                  m['doc'].strip() if m.get('doc') else '_No documentation._', '']
        if m.get('fields'):
            lines += ['Fields: ' + ', '.join(
                _code(f['name']) + (f' → {_code(f["related"])}' if f['related'] else f' ({f["type"]})')
                for f in m['fields']), '']


def render_markdown(data, audience='agent'):
    """
    The skill file of ``data`` (see ``teach_data.build_skill_data``).

    :param audience: ``agent`` (coding agents driving a browser: everything) or ``assistant`` (the in-app AI
                     assistant: without developer details such as the ready check, socket traffic, handler names
                     of forms and server views)
    """
    agent = audience == 'agent'
    project = data['project']
    actions = _actions_of(data)
    lines = [
        '---',
        f'name: {project.lower()}-ui',
        f'description: Map of the {project} web UI (SimpleDomControl). Use it to navigate views, '
        f'pass view arguments, click buttons and fill forms in {project}.',
        '---',
        '',
        f'# {project} UI map',
        '',
        f'Generated by `manage.py sdc_teach` on {data["date"]}. Crawled as: {", ".join(data["crawled_as"])}. '
        f'All paths are relative to the site root.',
        '',
        SDC_URL_GUIDE,
        '',
        '## How to operate this app',
        '',
    ]
    lines += [f'- {rule}' for rule in RULES + (AGENT_RULES if agent else [])]
    lines.append('')

    g = data['global']
    if any(g.get(k) for k in ('links', 'buttons', 'forms')) or (agent and g.get('model_calls')):
        lines += ['## Global navigation (always visible)', '']
        lines += [f'- {_link_line(l)}' for l in g.get('links', []) if l.get('target')]
        lines += [f'- {_button_line(b, actions, agent)}' for b in g.get('buttons', [])]
        lines += [f'- {_form_line(f, agent)}' for f in g.get('forms', [])]
        if agent and g.get('model_calls'):
            lines.append('- Model socket (on load):')
            _render_model_calls(g['model_calls'], '  ', lines)
        lines.append('')

    if data['views']:
        lines += ['## Views', '']
        for view in data['views']:
            _render_view(view, actions, lines, agent)
    _render_controllers(data['embedded'], lines, '## Embedded controllers',
                        'Controllers shown inside the views above (or globally).', agent)
    # Views without a link (detail and edit pages, views of other roles) are not reached by the crawl; their
    # documentation is still part of the app, so the skill file does not know less than the apps' SDC_SKILL.json.
    _render_controllers(
        data['unreached'], lines, '## Controllers not reached by the crawl',
        'No link or button of the crawled views opened these controllers (they may need arguments, other '
        'permissions or are only embedded by code). Their behaviour was not observed; the paths and arguments '
        'are not verified.', agent)
    _render_models(data['models'], lines)

    if data['errors'] and agent:
        lines += ['## Errors observed while crawling', '']
        lines += [f'- `/{url}`: {err}' for err, url in data['errors'][:50]]
        lines.append('')

    return '\n'.join(lines)


def render_skill(tree, meta, audience='agent'):
    """
    The skill file of a crawl.

    :param tree: ``{'nodes': {key: node}, 'errors': [...], 'global': {...}}`` from ``Crawler.crawl`` / ``merge_crawls``
    :param meta: ``project``, ``crawled_as`` (list), ``logged_in_label``,
                 ``controller_infos`` (``{tag: {'app', 'view_class', 'url', 'doc', 'actions'}}``, ``actions``:
                 ``{handler: doc}``), optional ``models`` (``[{'name', 'app', 'doc'}]``, see
                 ``teach_models.sdc_models``) and optional ``date``
    """
    return render_markdown(build_skill_data(tree, meta), audience)
