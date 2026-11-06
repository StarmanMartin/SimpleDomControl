"""Headless crawler used by ``manage.py sdc_teach``.

It drives a running SDC project with Playwright, follows every
``.navigation-links`` element of the ``sdc-navigator`` and clicks every
clickable element (``[sdc_click]``, buttons, ...) to build a tree of
navigation states. Each state records its controllers, arguments, links,
buttons, forms and the SdcModel WebSocket messages sent by each controller.
The result is a plain dict tree that ``teach_markdown.render_skill`` turns
into a skill file.

Every collected element carries ``nav_idx``: the navigator depth of the view
it belongs to (``None`` for global elements such as the navbar). Elements of
inactive (hidden) view containers are dropped.
"""
import json
import re
from collections import deque
from urllib.parse import parse_qs

SKIP_ALL = '__skip_all__'
# Page elements that are not part of the app: hidden while crawling (e.g. the fixed AI assistant panel would cover
# buttons at the right edge) and left out of every snapshot
CRAWL_IGNORED = 'sdc-ai-assistant'
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
    const ignored = (el) => !!el.closest(__IGNORED__);
    const scoped = (els, fn) => els.map((el) => {
        if (ignored(el)) return null;
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
        visible: visible(f),
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
}""".replace('__IGNORED__', json.dumps(CRAWL_IGNORED))

# Injected into every crawled page: hides the elements of CRAWL_IGNORED, so they cannot cover the app's buttons
HIDE_IGNORED_JS = """(() => {
    // Init scripts run before <html> exists: the style is added as soon as the document is parsed
    document.addEventListener('DOMContentLoaded', () => {
        const style = document.createElement('style');
        style.textContent = __IGNORED__ + ' { display: none !important; }';
        document.documentElement.appendChild(style);
    });
})();""".replace('__IGNORED__', json.dumps(CRAWL_IGNORED))


# Injected into every crawled page: logs each message sent over an SdcModel WebSocket together with the
# controller owning the queryset (``controller._models``). ``Crawler._model_calls`` reads and clears the log.
MODEL_LOG_JS = r"""(() => {
    const send = WebSocket.prototype.send;
    const log = window.__sdcModelLog = [];
    const keys = (o) => (o && typeof o === 'object' ? Object.keys(o).sort() : []);
    const empty = (v) => v === null || v === undefined || v === '' || (typeof v === 'object' && !keys(v).length);
    const controllerOf = (ws) => {
        if (!window.$) return null;
        for (const el of document.querySelectorAll('._sdc_controller_')) {
            const c = $(el).data('_controller_');
            if (c && (c._models || []).some((q) => q && q.socket === ws)) return c._tagName || el.tagName.toLowerCase();
        }
        return null;
    };
    WebSocket.prototype.send = function (data) {
        try {
            const msg = typeof data === 'string' && data.includes('"model"') ? JSON.parse(data) : null;
            if (msg && msg.event === 'model' && log.length < 1000) {
                const args = msg.args || {};
                log.push({
                    controller: controllerOf(this),
                    model: args.model_name,
                    event_type: msg.event_type,
                    query: keys(args.model_query),
                    args: keys(args).filter((k) => k !== 'model_name' && k !== 'model_query' && !empty(args[k])),
                });
            }
        } catch (e) {
            // never break the app because of the crawler
        }
        return send.call(this, data);
    };
})();"""


# Injected into the headed browser when the developer is asked to fill in a form. It highlights the
# form, shows a banner with skip buttons and stores the answer in sessionStorage (survives reloads).
ASK_FORM_JS = r"""(() => {
    const fieldNames = __FIELDS__;
    // Positional selectors are unreliable (the navigator swaps its view containers), so the
    // form is found by its field names among the visible forms.
    const isTarget = (form) => !!(form.offsetWidth || form.offsetHeight)
        && fieldNames.every((name) => form.querySelector(`[name="${CSS.escape(name)}"], #${CSS.escape(name)}`));
    const answer = (value) => {
        sessionStorage.setItem('__sdcTeach', value);
        window.__sdcTeach = value;
    };
    document.addEventListener('submit', (ev) => {
        if (ev.target.dataset.sdcTeach) answer('submitted');
    }, true);
    document.addEventListener('DOMContentLoaded', () => {
        const banner = document.createElement('div');
        banner.style.cssText = 'position:fixed;z-index:2147483647;left:0;right:0;bottom:0;padding:12px 16px;' +
            'background:#1f2937;color:#fff;font:14px sans-serif;display:flex;gap:12px;align-items:center';
        banner.innerHTML = '<span style="flex:1">sdc_teach: please fill in the highlighted <b></b> form ' +
            'and submit it. The crawler records what happens.</span>' +
            '<button data-a="skip">Skip</button><button data-a="skip_all">Skip all forms</button>';
        banner.querySelector('b').textContent = __LABEL__;
        banner.addEventListener('click', (ev) => ev.target.dataset.a && answer(ev.target.dataset.a));
        // Must be appended to <html>, not <body>: if body (or any wrapper) carries a CSS
        // transform/filter/zoom, `position: fixed` becomes relative to that element's box and the
        // banner ends up at the bottom of the document, below the visible viewport.
        document.documentElement.appendChild(banner);
        document.body.style.paddingBottom = '80px';  // keep the banner from covering submit buttons
        setInterval(() => {
            const form = [...document.forms].find(isTarget);
            if (form && !form.dataset.sdcTeach) {
                form.dataset.sdcTeach = '1';
                form.style.outline = '3px solid #f59e0b';
                form.scrollIntoView({block: 'center'});
            }
        }, 300);
    });
})();"""


def state_key(path, args):
    """Two states are the same view when the controller path and the arg *names* match."""
    return '~'.join(path) + '?' + ','.join(sorted(args or {}))


class Crawler:
    def __init__(self, context, base_url, start='/', max_depth=5, max_nodes=200, click=True,
                 click_all=False, deny=None, timeout=10000, log=print, label='anonymous',
                 ask_browser=None, form_cache=None, extra_paths=None):
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
        # Paths opened in addition to the links (e.g. the generic views of every SDC model); every visited path is
        # recorded in ``visits``: ``{href: {label: error code or None}}``
        self.extra_paths = list(extra_paths or [])
        self.visits = {}
        self.global_items = None
        self.errors = []
        self._calls = []
        self._dialogs = []
        self.page = None
        # ask_browser() returns a headed browser; forms are then filled in by the developer
        self.ask_browser = ask_browser
        self.form_cache = {} if form_cache is None else form_cache
        # Controller paths of ancestor views already documented by some node
        self._claimed = set()

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
            # Model socket messages are logged in the page by MODEL_LOG_JS, which also knows the controller
            if data.get('event') == 'sdc_call':
                self._calls.append({'via': 'websocket', 'target': f'{data.get("app")}.{data.get("controller")}',
                                    'function': data.get('function'), 'args': sorted(args)})

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

    def _model_calls(self):
        """Reads and clears the SdcModel socket log of the page (duplicates removed)."""
        try:
            log = self.page.evaluate('() => (window.__sdcModelLog || []).splice(0)')
        except Exception:  # noqa: BLE001 - the page may be navigating or closed
            return []
        calls = []
        for entry in log:
            call = {'via': 'model-socket', 'controller': entry.get('controller'), 'target': entry.get('model'),
                    'function': entry.get('event_type'), 'query': entry.get('query') or [],
                    'args': entry.get('args') or []}
            if call not in calls:
                calls.append(call)
        return calls

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
        return [i for i in items if i['nav_idx'] in (idx if isinstance(idx, (list, set)) else [idx])]

    def _owned_levels(self, path):
        """
        The node's own view level plus every ancestor level that never becomes a node of its own
        (e.g. a dashboard that always loads a default child view). The first node seeing such an
        ancestor claims its links, buttons and forms; otherwise they would never be crawled.
        """
        levels = [len(path) - 1]
        for i in range(len(path) - 1):
            prefix = tuple(path[:i + 1])
            if prefix not in self._claimed and not any(tuple(n['path']) == prefix for n in self.nodes.values()):
                self._claimed.add(prefix)
                levels.append(i)
        return levels

    # ----------------------------------------------------------------- crawl
    def crawl(self):
        self.context.add_init_script(MODEL_LOG_JS)
        self.context.add_init_script(HIDE_IGNORED_JS)
        self.page = self.context.new_page()
        self._attach(self.page)
        self._goto(self.start)
        root = self._snapshot()
        global_tags = {c['tag'] for c in self._own(root['controllers'], None)}
        self.global_items = {
            'links': self._own(root['links'], None),
            'external': self._own(root['external'], None),
            'buttons': [],
            'forms': self._own(root['forms'], None),
            'model_calls': [c for c in self._model_calls() if c['controller'] in global_tags],
        }
        if self.click:
            self.global_items['buttons'] = self._click_buttons(root['href'], self._own(root['buttons'], None), [])
        global_hrefs = []
        self.global_items['forms'] = self._ask_forms(root['href'], self.global_items['forms'], global_hrefs)
        queue = deque([(root['href'], 0, 'start')])
        queue.extend((h, 0, 'form') for h in global_hrefs)
        queue.extend((l['target']['href'], 0, f'link "{l["text"]}"')
                     for l in self.global_items['links'] if l['target'])
        queue.extend((path, 0, 'model route') for path in self.extra_paths)
        seen_hrefs = set()
        while queue and len(self.nodes) < self.max_nodes:
            href, depth, via = queue.popleft()
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            self._goto(href)
            snap = self._snapshot()
            model_calls = self._model_calls()
            idx = len(snap['path']) - 1
            codes = [c['error_code'] for c in snap['controllers']
                     if c.get('error_code') is not None and c['nav_idx'] == idx]
            self.visits[href] = {self.label: codes[0] if codes else None}
            key = state_key(snap['path'], snap['args'])
            if key in self.nodes:
                self._merge_examples(self.nodes[key], snap)
                continue
            self.log(f'[{self.label}] {"  " * depth}{snap["href"]}')
            node = self._make_node(key, snap, depth, via)
            own_tags = {c['tag'] for c in node['controllers']}
            node['model_calls'] = [c for c in model_calls if c['controller'] in own_tags]
            self.nodes[key] = node
            if depth >= self.max_depth:
                continue
            for link in node['links']:
                target = link['target']
                if target and target['href'] not in seen_hrefs:
                    queue.append((target['href'], depth + 1, f'link "{link["text"]}"'))
            if self.click:
                new_hrefs = []
                node['buttons'] = self._click_buttons(node['href'], self._own(snap['buttons'], node['owned_levels']),
                                                      new_hrefs)
                queue.extend((h, depth + 1, 'button') for h in new_hrefs)
            new_hrefs = []
            node['forms'] = self._ask_forms(node['href'], node['forms'], new_hrefs)
            queue.extend((h, depth + 1, 'form') for h in new_hrefs)
        self.page.close()
        return {'nodes': self.nodes, 'errors': self.errors, 'global': self.global_items, 'visits': self.visits}

    def _make_node(self, key, snap, depth, via):
        idx = len(snap['path']) - 1
        levels = self._owned_levels(snap['path'])
        own_controllers = self._own(snap['controllers'], levels)
        errors = [c['error_code'] for c in self._own(own_controllers, idx) if c.get('error_code') is not None]
        return {
            'key': key,
            'href': snap['href'],
            'path': snap['path'],
            'nav_idx': idx,
            'owned_levels': levels,
            'args': {k: [v] for k, v in snap['args'].items()},
            'depth': depth,
            'via': via,
            'seen_as': {self.label},
            'error_code': errors[0] if errors else None,
            'headings': [h['text'] for h in self._own(snap['headings'], idx)][:4],
            'controllers': own_controllers,
            'url_params': sorted({p for c in snap['controllers'] if c['tag'] in snap['path'] for p in c['url_params']}),
            'links': self._own(snap['links'], levels),
            'external': self._own(snap['external'], levels),
            'forms': self._own(snap['forms'], levels),
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
                self._model_calls()
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

    @staticmethod
    def _form_signature(form):
        return f'{form["controller"]}:' + ','.join(sorted(f['name'] for f in form['fields']))

    def _ask_forms(self, href, forms, new_hrefs):
        """Forms are never submitted automatically: the developer fills them in a headed browser."""
        for form in forms:
            if not form['visible'] or not form['fields']:
                continue
            signature = self._form_signature(form)
            if signature not in self.form_cache:
                ask = self.ask_browser and not self.form_cache.get(SKIP_ALL)
                self.form_cache[signature] = self._ask_developer(href, form) if ask else None
            result = self.form_cache[signature]
            if result is None:
                form['result'] = 'not submitted (needs manual input)'
                continue
            form.update(result)
            if result.get('navigates_to'):
                new_hrefs.append(result['navigates_to'])
        return forms

    def _ask_developer(self, href, form):
        browser = self.ask_browser()
        if browser is None:
            return None
        self.log(self._style_notice(
            f'Fill in the form of <{form["controller"]}> ({", ".join(f["name"] for f in form["fields"])}) '
            f'in the browser window and submit it, or click "Skip" in the banner.'))
        context = browser.new_context(storage_state=self.context.storage_state())
        context.add_init_script(MODEL_LOG_JS)
        context.add_init_script(HIDE_IGNORED_JS)
        context.add_init_script(ASK_FORM_JS.replace('__FIELDS__', json.dumps([f['name'] for f in form['fields'] if f['name']]))
                                .replace('__LABEL__', json.dumps(form['controller'] or 'form')))
        crawl_page, self.page = self.page, context.new_page()
        self._attach(self.page)
        try:
            self._goto(href)
            before = self._snapshot()
            self._calls.clear()
            self._dialogs.clear()
            self._model_calls()
            answer = self._wait_for_answer()
            if answer in ('skip', 'skip_all', 'closed'):
                if answer == 'skip_all':
                    self.form_cache[SKIP_ALL] = True
                return {'result': 'skipped by developer'}
            self.page.wait_for_timeout(500)
            self._wait_ready()
            after = self._snapshot()
            result = self._diff(before, after)
            result['result'] = 'submitted by developer'
            return result
        except Exception as e:  # noqa: BLE001 - a failing form must not stop the crawl
            return {'result': f'error: {str(e).splitlines()[0]}'}
        finally:
            self.page = crawl_page
            context.close()

    def _wait_for_answer(self):
        """Waits (without timeout) until the form was submitted, skipped or the window closed."""
        while True:
            try:
                handle = self.page.wait_for_function(
                    "() => window.__sdcTeach || sessionStorage.getItem('__sdcTeach')", timeout=0, polling=250)
                return handle.json_value()
            except Exception:  # noqa: BLE001 - reloads destroy the JS context, closing the window ends the wait
                if self.page.is_closed():
                    return 'closed'
                try:
                    answer = self.page.evaluate("() => sessionStorage.getItem('__sdcTeach')")
                except Exception:  # noqa: BLE001 - page is still navigating
                    answer = None
                if answer:
                    return answer

    @staticmethod
    def _style_notice(text):
        return f'\033[93m>>> {text}\033[0m'

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
        calls = self._calls + self._model_calls()
        if calls:
            effect['server_calls'] = calls
        if self._dialogs:
            effect['dialogs'] = list(self._dialogs)
        effect['result'] = 'clicked' if effect else 'clicked (no visible effect)'
        return effect


def merge_crawls(anonymous, logged_in):
    """
    Merges a logged-in crawl into the anonymous one (repeatedly, for several roles). A view that shows an error
    in the first crawl but works in the second is marked ``requires_login``; ``error_seen_as`` keeps the labels
    of the crawls that got an error view, so the skill file can say who may open a view.
    """
    nodes = dict(anonymous['nodes'])
    for key, node in logged_in['nodes'].items():
        old = nodes.get(key)
        if old is None:
            nodes[key] = node
            continue
        denied = set(old.get('error_seen_as') or ())
        if old['error_code'] is not None:
            # A role without the error view would have replaced the node: all of its roles got the error
            denied |= set(old['seen_as'])
        if node['error_code'] is not None:
            denied |= set(node['seen_as'])
        node['seen_as'] |= old['seen_as']
        for k, values in old['args'].items():
            node['args'].setdefault(k, [])
            node['args'][k] += [v for v in values if v not in node['args'][k]]
        if old['error_code'] is not None and node['error_code'] is None:
            node['requires_login'] = True
            node['error_seen_as'] = denied
            nodes[key] = node
        else:
            old['seen_as'] = node['seen_as']
            old['args'] = node['args']
            old['error_seen_as'] = denied
    global_items = anonymous['global']
    for name in ('links', 'buttons', 'model_calls'):
        known = {json.dumps(i, sort_keys=True, default=str) for i in global_items.setdefault(name, [])}
        global_items[name] += [i for i in logged_in['global'].get(name, [])
                               if json.dumps(i, sort_keys=True, default=str) not in known]
    visits = {href: dict(labels) for href, labels in (anonymous.get('visits') or {}).items()}
    for href, labels in (logged_in.get('visits') or {}).items():
        visits.setdefault(href, {}).update(labels)
    return {'nodes': nodes, 'errors': anonymous['errors'] + logged_in['errors'], 'global': global_items,
            'visits': visits}
