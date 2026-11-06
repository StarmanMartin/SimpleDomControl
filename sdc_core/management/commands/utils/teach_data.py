"""
Structured skill data of ``manage.py sdc_teach``: the crawl tree of ``teach_crawler`` merged with the
documentation of controllers and models, one entry per view.

``teach_markdown.render_markdown`` renders it as the skill file; ``sdc_teach`` also writes it as
``SDC_SKILL.data.json`` (``FORMAT`` is its version), so tools can use the knowledge without parsing Markdown.
"""
import datetime
import re

FORMAT = 1

# The generic views of an SDC model (see teach_models.model_views): controller tag and path; <id> is a record id
MODEL_ROUTES = {
    'list': ('sdc-list-view', '/~sdc-list-view~&model={model}'),
    'detail': ('sdc-detail-view', '/~sdc-detail-view~&model={model}&pk=<id>'),
    'create': ('sdc-model-form', '/~sdc-model-form~&model={model}'),
    'edit': ('sdc-model-form', '/~sdc-model-form~&model={model}&pk=<id>'),
}


def model_routes(model, infos):
    """``{kind: path}`` of the generic views the model supports and the project has installed."""
    views = model.get('views') or {}
    return {kind: path.format(model=model['name']) for kind, (tag, path) in MODEL_ROUTES.items()
            if views.get(kind) and tag in infos}


def route_paths(models, infos, pks):
    """
    The paths the crawler opens to verify the model routes: ``<id>`` is replaced by an existing record id
    (``pks``: ``{model name: id}``); routes with ``<id>`` of models without records are left out.
    """
    paths = []
    for model in models:
        for path in model_routes(model, infos).values():
            if '<id>' in path:
                if model['name'] not in pks:
                    continue
                path = path.replace('<id>', str(pks[model['name']]))
            paths.append(path)
    return paths


def _verified(path, visits):
    """``{'ok': [labels], 'denied': [labels]}`` of the crawl visits of a route (``<id>`` matches any id)."""
    pattern = re.compile(re.escape(path).replace(re.escape('<id>'), r'\d+') + '$')
    ok, denied = set(), set()
    for href, labels in visits.items():
        if pattern.match(href):
            for label, code in labels.items():
                (denied if code is not None else ok).add(label)
    return {'ok': sorted(ok), 'denied': sorted(denied - ok)}


def url_params(url):
    """The parameters of a Django URL pattern: ``/sdc_view/x/y/<int:pk>`` -> ``['pk']``."""
    return re.findall(r'<(?:\w+:)?(\w+)>', url or '')


def _own_args(node):
    """
    The arguments of the view itself (the deepest of its path), without the depth prefix: ``2.pk`` of a view at
    depth 2 is ``pk``. Arguments of parent views stay with their parents.
    """
    depth = len(node['path'])
    args = {}
    for key, values in node['args'].items():
        prefix, dot, name = key.partition('.')
        if dot and prefix.isdigit():
            if int(prefix) != depth:
                continue
            key = name
        args.setdefault(key, [])
        args[key] += [v for v in values if v not in args[key]]
    return args


def _merge_unique(target, items, key):
    seen = {key(i) for i in target}
    for item in items:
        if key(item) not in seen:
            seen.add(key(item))
            target.append(item)


def _link_key(link):
    return link['text'], (link.get('target') or {}).get('href')


def _button_key(button):
    return button['text'], tuple(button['handlers']), button.get('controller')


def _form_key(form):
    return form.get('controller'), tuple(sorted(f['name'] for f in form['fields']))


def _call_key(call):
    return call.get('controller'), call.get('target'), call.get('function'), tuple(call.get('query') or [])


def _info(tag, infos):
    """The documentation of a controller (see ``teach_controllers.sdc_controllers``), JSON-safe."""
    info = infos.get(tag) or {}
    return {
        'doc': info.get('doc'),
        'app': info.get('app'),
        'view_class': info.get('view_class'),
        'url': info.get('url'),
        'url_params': url_params(info.get('url')),
        'actions': dict(info.get('actions') or {}),
        'hidden': bool(info.get('hidden')),
        'summary': info.get('summary'),
        'tasks': list(info.get('tasks') or []),
    }


def build_skill_data(tree, meta):
    """
    :param tree: ``{'nodes': {key: node}, 'errors': [...], 'global': {...}}`` from ``Crawler.crawl`` /
                 ``merge_crawls``
    :param meta: ``project``, ``crawled_as`` (list), ``logged_in_label``, ``controller_infos``
                 (``{tag: {'app', 'view_class', 'url', 'doc', 'actions'}}``), optional ``models`` and ``date``
    :return: ``{'format', 'project', 'date', 'crawled_as', 'global', 'views', 'embedded', 'unreached', 'models',
               'errors'}``; ``views`` has one entry per controller tag that the navigator showed as the deepest
               view of a path, with all paths it was seen at (``paths``, shortest first).
    """
    infos = meta.get('controller_infos') or {}
    logged_in_label = meta.get('logged_in_label', 'logged-in')
    crawled_as = list(meta['crawled_as'])
    nodes = sorted(tree['nodes'].values(), key=lambda n: (len(n['path']), len(n['args']), n['href']))

    views = {}
    for node in nodes:
        tag = node['path'][-1] if node['path'] else '(root)'
        view = views.get(tag)
        if view is None:
            view = views[tag] = {
                'tag': tag, 'href': node['href'], 'paths': [], 'args': {}, 'seen_as': set(), 'denied': set(),
                'requires_login': False, 'errors': [], 'headings': list(node['headings'][:2]), 'embedded': set(),
                'links': [], 'buttons': [], 'forms': [], 'external': [], 'model_calls': [],
                'url_params': list(node.get('url_params') or []),
            } | _info(tag, infos)
        if node['href'] not in view['paths']:
            view['paths'].append(node['href'])
        for key, values in _own_args(node).items():
            view['args'].setdefault(key, [])
            view['args'][key] += [v for v in values if v not in view['args'][key] and len(view['args'][key]) < 5]
        view['seen_as'] |= set(node['seen_as'])
        view['denied'] |= set(node.get('error_seen_as') or ())
        if node['error_code'] is not None:
            view['denied'] |= set(node['seen_as'])
        if node.get('requires_login') or node['seen_as'] == {logged_in_label}:
            view['requires_login'] = True
        if node['error_code'] is not None:
            error = {'code': node['error_code'], 'seen_as': sorted(node['seen_as']), 'path': node['href']}
            if error not in view['errors']:
                view['errors'].append(error)
        view['embedded'] |= {c['tag'] for c in node['controllers']} - set(node['path'])
        _merge_unique(view['links'], [l for l in node['links'] if l.get('target')], _link_key)
        _merge_unique(view['buttons'], node['buttons'], _button_key)
        _merge_unique(view['forms'], node['forms'], _form_key)
        _merge_unique(view['external'], node['external'], lambda e: e['href'])
        _merge_unique(view['model_calls'], node.get('model_calls') or [], _call_key)

    view_list = []
    for view in views.values():
        # Who may open the view: the crawls that saw it without an error view
        view['available_to'] = sorted(view['seen_as'] - view['denied'])
        view['denied'] = sorted(view['denied'] - set(view['available_to']))
        if 'anonymous' in view['denied'] and view['available_to']:
            view['requires_login'] = True
        # The error views are explained by the roles: keep only those of views nobody could open
        if view['available_to']:
            view['errors'] = []
        view['seen_as'] = sorted(view['seen_as'])
        view['embedded'] = sorted(view['embedded'] - set(views))
        view_list.append(view)
    view_list.sort(key=lambda v: (len(v['paths'][0].split('~')), v['paths'][0]))

    seen_tags = set(views) | {t for v in view_list for t in v['embedded']}
    for node in nodes:
        seen_tags |= {c['tag'] for c in node['controllers']} | set(node['path'])
    global_items = tree.get('global') or {}
    seen_tags |= {c.get('controller') for c in global_items.get('buttons', []) if c.get('controller')}
    embedded = sorted(seen_tags - set(views) - {None})

    return {
        'format': FORMAT,
        'generator': 'manage.py sdc_teach',
        'project': meta['project'],
        'date': meta.get('date', datetime.date.today().isoformat()),
        'crawled_as': crawled_as,
        'global': {k: list(global_items.get(k) or []) for k in ('links', 'buttons', 'forms', 'model_calls')},
        'views': view_list,
        'embedded': [{'tag': tag} | _info(tag, infos) for tag in embedded if tag in infos],
        'unreached': [{'tag': tag} | _info(tag, infos) for tag in sorted(set(infos) - seen_tags)],
        'models': [{'name': m['name'], 'app': m.get('app'), 'doc': m.get('doc'), 'fields': m.get('fields') or [],
                    'routes': {kind: {'path': path} | _verified(path, tree.get('visits') or {})
                               for kind, path in model_routes(m, infos).items()},
                    'remove_in_list': bool((m.get('views') or {}).get('remove'))}
                   for m in meta.get('models') or []],
        'tasks': [{'controller': tag} | task for tag, info in sorted(infos.items()) for task in info.get('tasks') or []
                  if not info.get('hidden')],
        'errors': sorted({(e['error'], e['url'].split('/', 3)[-1]) for e in tree.get('errors', [])}),
    }
