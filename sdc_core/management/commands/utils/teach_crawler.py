"""Headless crawler used by ``manage.py sdc_teach``.

It drives a running SDC project with Playwright, follows every
``.navigation-links`` element of the ``sdc-navigator`` and clicks every
clickable element (``[sdc_click]``, buttons, ...) to build a tree of
navigation states. Each state records its controllers, arguments, links,
buttons and forms. The result is a plain dict tree that
``teach_markdown.render_skill`` turns into a skill file.

Every collected element carries ``nav_idx``: the navigator depth of the view
it belongs to (``None`` for global elements such as the navbar). Elements of
inactive (hidden) view containers are dropped.
"""
import json
import re
from collections import deque
from urllib.parse import parse_qs

DEFAULT_DENY = r'log ?out|sign ?out|delete|remove|destroy|drop|reset|submit|save|löschen|abmelden'

WAIT_READY_JS = """() => !!window.sdcNav
    && !window.sdcNav._is_processing
    && !document.querySelector('.sdc_sub_detail_container.loading')
    && !document.querySelector('.header-loading.active')"""

SNAPSHOT_JS = r"""() => {
    const nav = window.sdcNav;
    const clean = (s) => (s || '').replace(/\s+/g, ' ').trim().slice(0, 80);
    const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    const controllerOf = (el) => {
        const $c = $(el).closest('._sdc_controller_');
        if (!$c.length) return null;
        const c = $c.data('_controller_');
        return (c && c._tagName) || $c.prop('tagName').toLowerCase();
    };
    // nav_idx of the view container an element lives in; active = all enclosing view containers are active
    const scopeOf = (el) => {
        let box = el.closest('.sdc_sub_detail_container');
        if (!box) return {nav_idx: null, active: true};
        const nav_idx = parseInt(box.dataset.navIdx);
        let active = true;
        while (box) {
            if (!box.classList.contains('active')) active = false;
            box = box.parentElement && box.parentElement.closest('.sdc_sub_detail_container');
        }
        return {nav_idx, active};
    };
    const scoped = (els, fn) => els.map((el) => {
        const scope = scopeOf(el);
        return scope.active ? {...fn(el), nav_idx: scope.nav_idx} : null;
    }).filter(Boolean);
    const cssPath = (el) => {
        const parts = [];
        while (el && el.nodeType === 1 && el !== document.body) {
            if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
            let idx = 1, sib = el;
            while ((sib = sib.previousElementSibling)) if (sib.tagName === el.tagName) idx++;
            // tag names like <this.view_func> contain dots and must be escaped
            parts.unshift(CSS.escape(el.tagName.toLowerCase()) + ':nth-of-type(' + idx + ')');
            el = el.parentElement;
        }
        return (parts[0] && parts[0].startsWith('#') ? '' : 'body > ') + parts.join(' > ');
    };
    const resolve = (href) => {
        try {
            const s = nav._handleUrl(nav._prepareUrl(href));
            return {href: s.href, path: s.path, args: s.args};
        } catch (e) {
            return null;
        }
    };

    const state = nav._handleUrl(location.pathname);

    const controllers = scoped($('._sdc_controller_').toArray(), (el) => {
        const c = $(el).data('_controller_') || {};
        return {
            tag: c._tagName || el.tagName.toLowerCase(),
            url_params: [...(c._urlParams || [])],
            parent: c._parentController ? c._parentController._tagName : null,
            error_code: c._tagName === 'sdc-error' ? $(el).data('code') : undefined,
        };
    });

    const links = scoped($('.navigation-links[href]').toArray(), (a) => ({
        text: clean(a.innerText || a.title || a.getAttribute('aria-label')),
        raw_href: $(a).data('_origin_href') || a.getAttribute('href'),
        target: resolve($(a).data('_origin_href') || a.getAttribute('href')),
        controller: controllerOf(a),
        only_logged_in: a.classList.contains('only-logged-in'),
        only_logged_out: a.classList.contains('only-logged-out'),
    }));

    const external = scoped($('a[href]').not('.navigation-links').toArray(), (a) => ({
        text: clean(a.innerText || a.title),
        href: a.getAttribute('href'),
        controller: controllerOf(a),
    })).filter((l) => l.href && !l.href.startsWith('#') && !l.href.startsWith('javascript:'));

    const clickSel = '[sdc_click], button, [role=button], input[type=button], input[type=submit], a:not([href])';
    const buttons = scoped($(clickSel).not('.navigation-links').toArray(), (el) => ({
        text: clean(el.innerText || el.value || el.getAttribute('aria-label') || el.title),
        handlers: (el.getAttribute('sdc_click') || '').split(' ').filter(Boolean)
            .map((h) => h.startsWith('this.event_') ? 'events.click["' + h.slice(11) + '"]' : h),
        type: el.getAttribute('type') || '',
        classes: typeof el.className === 'string' ? el.className : '',
        toggles: el.getAttribute('data-bs-toggle') || '',
        controller: controllerOf(el),
        selector: cssPath(el),
        visible: visible(el),
        in_form: !!el.closest('form'),
    }));

    const forms = scoped($('form').toArray(), (f) => ({
        controller: controllerOf(f),
        action: f.getAttribute('action') || '',
        method: (f.getAttribute('method') || 'get').toLowerCase(),
        submit_handlers: (f.getAttribute('sdc_submit') || '').split(' ').filter(Boolean)
            .map((h) => h.startsWith('this.event_') ? 'events.submit["' + h.slice(11) + '"]' : h),
        fields: $(f).find('input, select, textarea').toArray()
            .filter((i) => !['hidden', 'submit', 'button'].includes(i.type) && i.name !== 'csrfmiddlewaretoken')
            .map((i) => ({
                name: i.name || i.id || '',
                type: i.tagName === 'SELECT' ? 'select' : (i.tagName === 'TEXTAREA' ? 'textarea' : (i.type || 'text')),
                required: !!i.required,
                label: clean((i.labels && i.labels[0] && i.labels[0].innerText) || i.placeholder || ''),
                options: i.tagName === 'SELECT' ? [...i.options].slice(0, 15).map((o) => clean(o.text)) : [],
            })),
    }));

    const headings = scoped($('h1, h2, h3, h4, legend, .card-title').toArray(), (h) => ({
        text: visible(h) ? clean(h.innerText) : '',
    })).filter((h) => h.text && h.nav_idx !== null);

    return {
        href: state.href,
        path: state.path,
        args: state.args,
        title: document.title,
        headings, controllers, links, external, buttons, forms,
        modal_open: !!document.querySelector('.modal.show'),
        alerts: $('.alert:visible').toArray().map((a) => clean(a.innerText)).filter(Boolean),
    };
}"""


def state_key(path, args):
    """Two states are the same view when the controller path and the arg *names* match."""
    return '~'.join(path) + '?' + ','.join(sorted(args or {}))


class Crawler:
    def __init__(self, context, base_url, start='/', max_depth=5, max_nodes=200, click=True,
                 click_all=False, deny=None, timeout=10000, log=print, label='anonymous'):
        self.context = context
        self.base_url = base_url.rstrip('/')
        self.start = start
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.click = click
        self.click_all = click_all
        self.deny = re.compile('|'.join(filter(None, [DEFAULT_DENY, deny])), re.IGNORECASE)
        self.timeout = timeout
        self.log = log
        self.label = label
        self.nodes = {}
        self.global_items = None
        self.errors = []
        self._calls = []
        self._dialogs = []
        self.page = None

    # ------------------------------------------------------------------ setup
    def _attach(self, page):
        page.set_default_timeout(self.timeout)
        page.on('pageerror', lambda exc: self.errors.append({'url': page.url, 'error': str(exc)}))
        page.on('console', lambda msg: msg.type == 'error' and self.errors.append(
            {'url': page.url, 'error': msg.text}))
        page.on('dialog', self._on_dialog)
        page.on('websocket', self._on_websocket)
        page.on('request', self._on_request)

    def _on_dialog(self, dialog):
        self._dialogs.append(f'{dialog.type}: {dialog.message}')
        dialog.dismiss()

    def _on_websocket(self, ws):
        def on_frame(payload):
            try:
                data = json.loads(payload)
            except (TypeError, ValueError):
                return
            if not isinstance(data, dict):
                return
            args = data.get('args') if isinstance(data.get('args'), dict) else {}
            if data.get('event') == 'sdc_call':
                self._calls.append({'via': 'websocket', 'target': f'{data.get("app")}.{data.get("controller")}',
                                    'function': data.get('function'), 'args': sorted(args)})
            elif data.get('event') == 'model' and data.get('event_type') != 'connect':
                self._calls.append({'via': 'model-socket', 'target': args.get('model_name'),
                                    'function': data.get('event_type'),
                                    'args': sorted(k for k, v in args.items() if v not in (None, '', {}))})

        ws.on('framesent', on_frame)

    def _on_request(self, request):
        if request.method != 'POST':
            return
        try:
            data = parse_qs(request.post_data or '')
        except (TypeError, ValueError):
            return
        if data.get('_method', [''])[0] == 'sdc_server_call':
            try:
                args = sorted(json.loads(data.get('data', ['{}'])[0]).keys())
            except (TypeError, ValueError, AttributeError):
                args = []
            self._calls.append({'via': 'http', 'target': request.url.replace(self.base_url, ''),
                                'function': data.get('_sdc_func_name', [''])[0], 'args': args})

    # --------------------------------------------------------------- helpers
    def _goto(self, url):
        self.page.goto(url if url.startswith('http') else self.base_url + url, wait_until='domcontentloaded')
        self._wait_ready()

    def _wait_ready(self):
        try:
            self.page.wait_for_function(WAIT_READY_JS, timeout=self.timeout)
            self.page.wait_for_load_state('networkidle', timeout=self.timeout)
        except Exception as e:  # noqa: BLE001 - a slow page must not stop the crawl
            self.errors.append({'url': self.page.url, 'error': f'not ready: {e}'.splitlines()[0]})

    def _snapshot(self):
        return self.page.evaluate(SNAPSHOT_JS)

    def _is_denied(self, btn):
        if self.click_all:
            return False
        if btn['type'] == 'submit' or btn['in_form']:
            return True
        text = ' '.join([btn['text'], ' '.join(btn['handlers']), btn['classes']])
        return bool(self.deny.search(text))

    @staticmethod
    def _own(items, idx):
        return [i for i in items if i['nav_idx'] == idx]

    # ----------------------------------------------------------------- crawl
    def crawl(self):
        self.page = self.context.new_page()
        self._attach(self.page)
        self._goto(self.start)
        root = self._snapshot()
        self.global_items = {
            'links': self._own(root['links'], None),
            'external': self._own(root['external'], None),
            'buttons': [],
            'forms': self._own(root['forms'], None),
        }
        if self.click:
            self.global_items['buttons'] = self._click_buttons(root['href'], self._own(root['buttons'], None), [])
        queue = deque([(root['href'], 0, 'start')])
        queue.extend((l['target']['href'], 0, f'link "{l["text"]}"')
                     for l in self.global_items['links'] if l['target'])
        seen_hrefs = set()
        while queue and len(self.nodes) < self.max_nodes:
            href, depth, via = queue.popleft()
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            self._goto(href)
            snap = self._snapshot()
            key = state_key(snap['path'], snap['args'])
            if key in self.nodes:
                self._merge_examples(self.nodes[key], snap)
                continue
            self.log(f'[{self.label}] {"  " * depth}{snap["href"]}')
            node = self._make_node(key, snap, depth, via)
            self.nodes[key] = node
            if depth >= self.max_depth:
                continue
            for link in node['links']:
                target = link['target']
                if target and target['href'] not in seen_hrefs:
                    queue.append((target['href'], depth + 1, f'link "{link["text"]}"'))
            if self.click:
                new_hrefs = []
                node['buttons'] = self._click_buttons(node['href'], self._own(snap['buttons'], node['nav_idx']),
                                                      new_hrefs)
                queue.extend((h, depth + 1, 'button') for h in new_hrefs)
        self.page.close()
        return {'nodes': self.nodes, 'errors': self.errors, 'global': self.global_items}

    def _make_node(self, key, snap, depth, via):
        idx = len(snap['path']) - 1
        own_controllers = self._own(snap['controllers'], idx)
        errors = [c['error_code'] for c in own_controllers if c.get('error_code') is not None]
        return {
            'key': key,
            'href': snap['href'],
            'path': snap['path'],
            'nav_idx': idx,
            'args': {k: [v] for k, v in snap['args'].items()},
            'depth': depth,
            'via': via,
            'seen_as': {self.label},
            'error_code': errors[0] if errors else None,
            'headings': [h['text'] for h in self._own(snap['headings'], idx)][:4],
            'controllers': own_controllers,
            'url_params': sorted({p for c in snap['controllers'] if c['tag'] in snap['path'] for p in c['url_params']}),
            'links': self._own(snap['links'], idx),
            'external': self._own(snap['external'], idx),
            'forms': self._own(snap['forms'], idx),
            'buttons': [],
        }

    @staticmethod
    def _merge_examples(node, snap):
        for k, v in snap['args'].items():
            values = node['args'].setdefault(k, [])
            if v not in values and len(values) < 5:
                values.append(v)

    def _click_buttons(self, href, buttons, new_hrefs):
        results = []
        for btn in buttons:
            entry = {k: btn[k] for k in ('text', 'handlers', 'controller', 'toggles')}
            results.append(entry)
            if not btn['visible']:
                entry['result'] = 'hidden (not clicked)'
                continue
            if self._is_denied(btn):
                entry['result'] = 'skipped (denylist / form submit)'
                continue
            try:
                self._goto(href)
                before = self._snapshot()
                self._calls.clear()
                self._dialogs.clear()
                self.page.locator(btn['selector']).first.click(timeout=self.timeout)
                self.page.wait_for_timeout(300)
                self._wait_ready()
                after = self._snapshot()
            except Exception as e:  # noqa: BLE001 - one broken button must not stop the crawl
                entry['result'] = f'error: {str(e).splitlines()[0]}'
                continue
            entry.update(self._diff(before, after))
            if entry.get('navigates_to'):
                new_hrefs.append(entry['navigates_to'])
        return results

    def _diff(self, before, after):
        effect = {}
        if state_key(before['path'], before['args']) != state_key(after['path'], after['args']):
            effect['navigates_to'] = after['href']
        new_tags = sorted({c['tag'] for c in after['controllers']} - {c['tag'] for c in before['controllers']})
        if new_tags:
            effect['opens'] = new_tags
        if 'navigates_to' not in effect:
            before_headings = [h['text'] for h in before['headings']]
            changed = [h['text'] for h in after['headings'] if h['text'] not in before_headings]
            if changed:
                effect['updates'] = changed
            if len(after['controllers']) != len(before['controllers']):
                effect['controller_count'] = (len(before['controllers']), len(after['controllers']))
        if after['modal_open'] and not before['modal_open']:
            effect['modal'] = True
        new_alerts = [a for a in after['alerts'] if a not in before['alerts']]
        if new_alerts:
            effect['alerts'] = new_alerts
        if self._calls:
            effect['server_calls'] = list(self._calls)
        if self._dialogs:
            effect['dialogs'] = list(self._dialogs)
        effect['result'] = 'clicked' if effect else 'clicked (no visible effect)'
        return effect


def merge_crawls(anonymous, logged_in):
    """
    Merges a logged-in crawl into the anonymous one. A view that shows an error
    anonymously but works when logged in is marked ``requires_login``.
    """
    nodes = dict(anonymous['nodes'])
    for key, node in logged_in['nodes'].items():
        old = nodes.get(key)
        if old is None:
            nodes[key] = node
            continue
        node['seen_as'] |= old['seen_as']
        for k, values in old['args'].items():
            node['args'].setdefault(k, [])
            node['args'][k] += [v for v in values if v not in node['args'][k]]
        if old['error_code'] is not None and node['error_code'] is None:
            node['requires_login'] = True
            nodes[key] = node
        else:
            old['seen_as'] = node['seen_as']
            old['args'] = node['args']
    global_items = anonymous['global']
    for name in ('links', 'buttons'):
        known = {json.dumps(i, sort_keys=True, default=str) for i in global_items[name]}
        global_items[name] += [i for i in logged_in['global'][name]
                               if json.dumps(i, sort_keys=True, default=str) not in known]
    return {'nodes': nodes, 'errors': anonymous['errors'] + logged_in['errors'], 'global': global_items}
