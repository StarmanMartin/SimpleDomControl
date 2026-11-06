"""Renders the tree collected by ``teach_crawler.Crawler`` as a Markdown skill file for AI agents."""
import datetime
import re


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


def _tree_parent(node, nodes_by_path):
    """The tree parent is the node with the longest proper prefix of the controller path."""
    path = node['path']
    for i in range(len(path) - 1, 0, -1):
        parent = nodes_by_path.get(tuple(path[:i]))
        if parent:
            return parent['key']
    return None


def _model_call(call):
    query = f' filter {", ".join(map(_code, call["query"]))}' if call.get('query') else ''
    return f'`{call["target"]}.{call["function"]}({", ".join(call["args"])})`{query}'


def _call_text(call):
    if call['via'] == 'model-socket':
        source = f' from {_code(call["controller"])}' if call.get('controller') else ''
        return f'model-socket {_model_call(call)}{source}'
    return f'{call["via"]} call `{call["target"]}.{call["function"]}({", ".join(call["args"])})`'


def _render_model_calls(calls, pad, lines):
    by_controller = {}
    for call in calls:
        by_controller.setdefault(call['controller'] or '?', []).append(call)
    for controller, calls in sorted(by_controller.items()):
        lines.append(f'{pad}- {_code(controller)}: ' + '; '.join(map(_model_call, calls)))


def _effects(b):
    """Describes the observed outcome of a clicked button or a submitted form."""
    effect = [b.get('result', '')]
    if b.get('navigates_to'):
        effect.append(f'navigates to {_code(b["navigates_to"])}')
    if b.get('opens'):
        effect.append('shows ' + ', '.join(map(_code, b['opens'])))
    if b.get('updates'):
        effect.append('updates view: ' + ', '.join(f'"{t}"' for t in b['updates']))
    if b.get('controller_count'):
        effect.append('controllers {} → {}'.format(*b['controller_count']))
    if b.get('modal'):
        effect.append('opens a modal')
    if b.get('toggles'):
        effect.append(f'bootstrap toggle `{b["toggles"]}`')
    for call in b.get('server_calls', []):
        effect.append(_call_text(call))
    for alert in b.get('alerts', []):
        effect.append(f'alert "{alert}"')
    for dialog in b.get('dialogs', []):
        effect.append(f'dialog "{dialog}"')
    return '; '.join(filter(None, effect))


def _summary(doc):
    """The first paragraph of a doc comment on one line."""
    return ' '.join((doc or '').strip().split('\n\n')[0].split())


def _action_docs(button, infos):
    """The documented actions (JSDoc of the ``sdc_click`` handlers) of a button."""
    actions = (infos.get(button.get('controller')) or {}).get('actions') or {}
    return [f'`{h}()`: {_summary(actions[h])}' for h in button['handlers'] if actions.get(h)]


def _render_buttons(buttons, pad, lines, infos=None):
    for b in buttons:
        handler = ', '.join(f'`{h}()`' for h in b['handlers']) or 'no sdc_click handler'
        docs = _action_docs(b, infos or {})
        lines.append(f'{pad}- "{b["text"] or "(no label)"}" in {_code(b["controller"])} → {handler} — '
                     f'{_effects(b)}' + (f' — action: {"; ".join(docs)}' if docs else ''))


def _render_forms(forms, pad, lines):
    for f in forms:
        fields = ', '.join(
            f'{_code(x["name"])} ({x["type"]}{", required" if x["required"] else ""}'
            f'{", options: " + "/".join(x["options"]) if x["options"] else ""})'
            for x in f['fields']) or 'no visible fields'
        submit = f'; submit → {", ".join(f"`{h}()`" for h in f["submit_handlers"])}' if f['submit_handlers'] else ''
        outcome = f' — {_effects(f)}' if f.get('result') else ''
        lines.append(f'{pad}- in {_code(f["controller"])}: {fields}{submit}{outcome}')


def _render_links(links, pad, lines):
    for l in links:
        if not l['target']:
            continue
        flags = ' _(logged in only)_' if l['only_logged_in'] else (
            ' _(logged out only)_' if l['only_logged_out'] else '')
        lines.append(f'{pad}- "{l["text"]}" → {_code(l["target"]["href"])}{flags}')


def _render_node(node, children, nodes, lines, indent, logged_in_label, infos=None):
    pad = '  ' * indent
    flags = []
    if node.get('requires_login') or node['seen_as'] == {logged_in_label}:
        flags.append('login required')
    if node['error_code'] is not None:
        flags.append(f'shows sdc-error {node["error_code"]} for {", ".join(sorted(node["seen_as"]))}')
    title = ' / '.join(node['headings'][:2])
    lines.append(f'{pad}- **{node["path"][-1] if node["path"] else "(root)"}** — {_code(node["href"])}'
                 + (f' — "{title}"' if title else '')
                 + (f' _({"; ".join(flags)})_' if flags else ''))
    pad += '  '

    if node['url_params']:
        lines.append(f'{pad}- Required URL params: {", ".join(map(_code, node["url_params"]))}')
    if node['args']:
        lines.append(f'{pad}- Arguments:')
        for key, values in sorted(node['args'].items()):
            examples = ', '.join(_code(v) for v in values[:5])
            lines.append(f'{pad}  - {_code(key)} ({_type_of(values)}), e.g. {examples}')
    embedded = sorted({c['tag'] for c in node['controllers']} - set(node['path']))
    if embedded:
        lines.append(f'{pad}- Embedded controllers: {", ".join(map(_code, embedded))}')
    if node['links']:
        lines.append(f'{pad}- Links:')
        _render_links(node['links'], pad + '  ', lines)
    if node['buttons']:
        lines.append(f'{pad}- Buttons:')
        _render_buttons(node['buttons'], pad + '  ', lines, infos)
    if node['forms']:
        lines.append(f'{pad}- Forms:')
        _render_forms(node['forms'], pad + '  ', lines)
    if node.get('model_calls'):
        lines.append(f'{pad}- Model socket (on load):')
        _render_model_calls(node['model_calls'], pad + '  ', lines)
    external = sorted({l['href'] for l in node['external']})
    if external:
        lines.append(f'{pad}- Non-SDC links: {", ".join(map(_code, external))}')

    for child in children.get(node['key'], []):
        _render_node(nodes[child], children, nodes, lines, indent + 1, logged_in_label, infos)


def url_params(url):
    return re.findall(r'<(?:\w+:)?(\w+)>', url or '')


def _render_controllers(tags, infos, lines, show_app=True, heading='## Controllers', intro=None):
    if not tags:
        return
    lines += [heading, '']
    if intro:
        lines += [intro, '']
    for tag in tags:
        info = infos.get(tag, {})
        params = url_params(info.get('url'))
        source = [f'app `{info["app"]}`' if show_app and info.get('app') else '',
                  f'server view {_code(info["view_class"])}' if info.get('view_class') else '',
                  f'Django URL {_code(info["url"])}' if info.get('url') else '',
                  f'required URL params {", ".join(map(_code, params))}' if params else '']
        lines += [f'### `<{tag}>`', '', info['doc'].strip() if info.get('doc') else '_No documentation._', '']
        if any(source):
            lines += ['_' + ', '.join(filter(None, source)) + '_', '']
        _render_actions(info.get('actions'), lines)


def _render_actions(actions, lines):
    """What the controller's buttons do: the JSDoc of every ``sdc_click`` handler of its template and code."""
    if not actions:
        return
    lines.append('Button actions (`sdc_click` handlers):')
    for handler, doc in sorted(actions.items()):
        lines.append(f'- `{handler}()`: ' + (_summary(doc) if doc else '_No documentation._'))
    lines.append('')


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


def render_skill(tree, meta):
    """
    :param tree: ``{'nodes': {key: node}, 'errors': [...], 'global': {...}}`` from ``Crawler.crawl`` / ``merge_crawls``
    :param meta: ``project``, ``crawled_as`` (list), ``logged_in_label``,
                 ``controller_infos`` (``{tag: {'app', 'view_class', 'url', 'doc', 'actions'}}``, ``actions``:
                 ``{handler: doc}``), optional ``models``
                 (``[{'name', 'app', 'doc'}]``, see ``teach_models.sdc_models``) and optional ``date``
    """
    nodes = tree['nodes']
    project = meta['project']
    logged_in_label = meta.get('logged_in_label', 'logged-in')
    nodes_by_path = {}
    for node in sorted(nodes.values(), key=lambda n: (len(n['args']), n['depth'])):
        nodes_by_path.setdefault(tuple(node['path']), node)

    children, roots = {}, []
    for node in sorted(nodes.values(), key=lambda n: (len(n['path']), n['href'])):
        parent = _tree_parent(node, nodes_by_path)
        if parent and parent != node['key']:
            children.setdefault(parent, []).append(node['key'])
        else:
            roots.append(node['key'])

    lines = [
        '---',
        f'name: {project.lower()}-ui',
        f'description: Map of the {project} web UI (SimpleDomControl). Use it to navigate views, '
        f'pass view arguments, click buttons and fill forms in {project}.',
        '---',
        '',
        f'# {project} UI map',
        '',
        f'Generated by `manage.py sdc_teach` on {meta.get("date", datetime.date.today().isoformat())}. '
        f'Crawled as: {", ".join(meta["crawled_as"])}. All paths are relative to the site root.',
        '',
        SDC_URL_GUIDE,
        '',
        '## How to operate this app',
        '',
        '- Links of the navigation tree are shown resolved by the `sdc-navigator` (absolute paths with the '
        'arguments of their view depth).',
        '- Buttons call controller methods named in their `sdc_click` attribute (`sdc_click="method"`); '
        '`events.click[".selector"]` marks handlers registered in the controller `events` list. '
        '"action:" and the "Button actions" of a controller describe what a handler does (its JSDoc); the '
        'observed effect of the crawl follows the arrow.',
        '- A view is ready when `window.sdcNav && !window.sdcNav._is_processing` and no '
        '`.sdc_sub_detail_container.loading` element exists.',
        '- Server calls (`this.serverCall(...)`) execute methods of the matching `SDCView` on the server; '
        'model-socket calls load/save model data.',
        '- Buttons marked "skipped" were not executed by the crawler because they look destructive '
        '(delete/logout/save/submit); their effect is unknown — confirm with the user before clicking them.',
        '- Forms were not submitted automatically; "submitted by developer" shows what a manual submit did, '
        '"not submitted" means the outcome is unknown.',
        '- A view showing `sdc-error 403` needs a logged-in user with the right permissions.',
        '- All SdcModel WebSocket traffic (`/sdc_ws/model/<Model>`) was recorded per controller: '
        '"Model socket (on load)" lists what each controller requests when the view opens, buttons and forms list '
        'what they trigger, as `Model.event(args)` with the `model_query` filter keys. `connect` subscribes to '
        'live updates of the filtered rows; `load`, `save`, `create`, `delete`, ... read or write data.',
        '',
    ]

    global_items = tree.get('global') or {}
    if any(global_items.get(k) for k in ('links', 'buttons', 'forms', 'model_calls')):
        lines += ['## Global navigation (always visible)', '']
        _render_links(global_items.get('links', []), '', lines)
        _render_buttons(global_items.get('buttons', []), '', lines, meta.get('controller_infos') or {})
        _render_forms(global_items.get('forms', []), '', lines)
        if global_items.get('model_calls'):
            lines.append('- Model socket (on load):')
            _render_model_calls(global_items['model_calls'], '  ', lines)
        lines.append('')

    lines += ['## Navigation tree', '']
    for key in roots:
        _render_node(nodes[key], children, nodes, lines, 0, logged_in_label, meta.get('controller_infos') or {})
    lines.append('')

    infos = meta.get('controller_infos') or {}
    seen_tags = sorted({c['tag'] for n in nodes.values() for c in n['controllers']}
                       | {t for n in nodes.values() for t in n['path']})
    _render_controllers(seen_tags, infos, lines)
    # Views without a link (detail and edit pages, views of other roles) are not reached by the crawl; their
    # documentation is still part of the app, so the skill file does not know less than the apps' SDC_SKILL.json.
    _render_controllers(
        sorted(set(infos) - set(seen_tags)), infos, lines, heading='## Controllers not reached by the crawl',
        intro='No link or button of the crawled views opened these controllers (they may need arguments, other '
              'permissions or are only embedded by code). Their behaviour was not observed; the paths and arguments '
              'are not verified.')
    _render_models(meta.get('models') or [], lines)

    errors = {(e['error'], e['url'].split('/', 3)[-1]) for e in tree.get('errors', [])}
    if errors:
        lines += ['## Errors observed while crawling', '']
        lines += [f'- `/{url}`: {err}' for err, url in sorted(errors)[:50]]
        lines.append('')

    return '\n'.join(lines)
