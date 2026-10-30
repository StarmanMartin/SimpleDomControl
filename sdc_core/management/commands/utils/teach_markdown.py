"""Renders the tree collected by ``teach_crawler.Crawler`` as a Markdown skill file for AI agents."""
import datetime
import re


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


def _render_buttons(buttons, pad, lines):
    for b in buttons:
        handler = ', '.join(f'`{h}()`' for h in b['handlers']) or 'no sdc_click handler'
        lines.append(f'{pad}- "{b["text"] or "(no label)"}" in {_code(b["controller"])} → {handler} — '
                     f'{_effects(b)}')


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


def _render_node(node, children, nodes, lines, indent, logged_in_label):
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
        _render_buttons(node['buttons'], pad + '  ', lines)
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
        _render_node(nodes[child], children, nodes, lines, indent + 1, logged_in_label)


def _url_params(url):
    return re.findall(r'<(?:\w+:)?(\w+)>', url or '')


def _render_controllers(tags, infos, lines, show_app=True):
    if not tags:
        return
    lines += ['## Controllers', '']
    for tag in tags:
        info = infos.get(tag, {})
        params = _url_params(info.get('url'))
        source = [f'app `{info["app"]}`' if show_app and info.get('app') else '',
                  f'server view {_code(info["view_class"])}' if info.get('view_class') else '',
                  f'Django URL {_code(info["url"])}' if info.get('url') else '',
                  f'required URL params {", ".join(map(_code, params))}' if params else '']
        lines += [f'### `<{tag}>`', '', info['doc'].strip() if info.get('doc') else '_No documentation._', '']
        if any(source):
            lines += ['_' + ', '.join(filter(None, source)) + '_', '']


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


def render_app_skill(app, controllers, models, meta):
    """
    Simplified skill file of one app: only its controllers and SDC models with their documentation.

    :param controllers: ``{tag: info}`` of the app (see ``teach_controllers.sdc_controllers``)
    :param models: the app's entries of ``teach_models.sdc_models``
    :param meta: ``project`` and optional ``date``
    """
    project = meta['project']
    lines = [
        '---',
        f'name: {app.lower().replace("_", "-")}',
        f'description: Controllers (views) and data models of the {app} app in {project} (SimpleDomControl). '
        f'Use it to know which views and models {app} provides, what they do and which arguments they take.',
        '---',
        '',
        f'# {app}: controllers and data models',
        '',
        f'Generated by `manage.py sdc_teach --per-app` on {meta.get("date", datetime.date.today().isoformat())}. '
        'Open a controller by navigating to `/~<tag>` (nested views: `/~parent~child`); arguments follow after '
        '`~&` as `key=value` pairs joined by `&` and reach the view as `data-*` attributes.',
        '',
    ]
    _render_controllers(sorted(controllers), controllers, lines, show_app=False)
    _render_models(models, lines, show_app=False)
    return '\n'.join(lines)


def render_skill(tree, meta):
    """
    :param tree: ``{'nodes': {key: node}, 'errors': [...], 'global': {...}}`` from ``Crawler.crawl`` / ``merge_crawls``
    :param meta: ``project``, ``crawled_as`` (list), ``logged_in_label``,
                 ``controller_infos`` (``{tag: {'app', 'view_class', 'url', 'doc'}}``), optional ``models``
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
        '## How to operate this app',
        '',
        '- The app is a single page. Views are SDC controllers nested by the `sdc-navigator`; '
        'the URL path lists them separated by `~`: `/~parent-view~child-view`.',
        '- Arguments follow after `~&` as `key=value` pairs joined by `&`: `/~main-view~&id=5`. '
        'A key may be prefixed with the view depth (`1.id`, `2.id`) to target one view of the path; '
        'arguments are handed to the view as `data-*` attributes / `this.params`.',
        '- Relative paths: `..` goes one view up, `*` keeps the current view at that depth, `.` is the current path '
        '(e.g. `..~other-view`).',
        '- Navigate in the browser with `window.sdcNav.goTo("/~view-a~view-b", {key: value})` '
        'or open the URL directly; links with class `navigation-links` do the same.',
        '- Buttons call controller methods named in their `sdc_click` attribute (`sdc_click="method"`); '
        '`events.click[".selector"]` marks handlers registered in the controller `events` list.',
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
        _render_buttons(global_items.get('buttons', []), '', lines)
        _render_forms(global_items.get('forms', []), '', lines)
        if global_items.get('model_calls'):
            lines.append('- Model socket (on load):')
            _render_model_calls(global_items['model_calls'], '  ', lines)
        lines.append('')

    lines += ['## Navigation tree', '']
    for key in roots:
        _render_node(nodes[key], children, nodes, lines, 0, logged_in_label)
    lines.append('')

    infos = meta.get('controller_infos') or {}
    seen_tags = sorted({c['tag'] for n in nodes.values() for c in n['controllers']}
                       | {t for n in nodes.values() for t in n['path']})
    _render_controllers(seen_tags, infos, lines)
    _render_models(meta.get('models') or [], lines)

    errors = {(e['error'], e['url'].split('/', 3)[-1]) for e in tree.get('errors', [])}
    if errors:
        lines += ['## Errors observed while crawling', '']
        lines += [f'- `/{url}`: {err}' for err, url in sorted(errors)[:50]]
        lines.append('')

    return '\n'.join(lines)
