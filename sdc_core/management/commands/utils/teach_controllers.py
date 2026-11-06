"""Reads and writes the JSDoc comment of client controller classes (``class XController extends AbstractSDC``)."""
import importlib
import os
import re
import textwrap

from django.urls import URLPattern, URLResolver, get_resolver

from sdc_core.management.commands.init_add.utils import convert_to_tag_name, convert_to_title_camel_case

CLASS_RE = r'^([ \t]*)(?:export[ \t]+(?:default[ \t]+)?)?class[ \t]+{name}[ \t]+extends\b'
# sdc_click="handler other" in templates and in HTML built by the controller code
SDC_CLICK_RE = re.compile(r'\bsdc_click\s*=\s*\\?["\']([^"\'\\]+)\\?["\']')
# A JSDoc block directly followed by a method definition: /** ... */ [static] [async] [*] name(
METHOD_DOC_RE = r'/\*\*((?:(?!\*/).)*?)\*/\s*(?:static\s+)?(?:async\s+)?\*?\s*{name}\s*\('


def controller_js_file(app, tag, url=''):
    """
    ``<app>/Assets/src/<app>/controller/<name>/<name>.js`` of the controller ``tag`` or ``None``. ``name`` is
    taken from the Django URL ``/sdc_view/<app>/<name>/...``; the tag alone is ambiguous (``error404`` is
    the controller ``error_404``).
    """
    try:
        app_path = os.path.dirname(importlib.import_module(app).__file__)
    except (ImportError, TypeError):
        return None
    parts = url.strip('/').split('/')
    name = parts[parts.index(app) + 1] if app in parts[:-1] else tag.replace('-', '_')
    file = os.path.join(app_path, 'Assets', 'src', app, 'controller', name, f'{name}.js')
    return file if os.path.isfile(file) else None


def _class_match(source, tag):
    name = re.escape(convert_to_title_camel_case(tag.replace('-', '_')) + 'Controller')
    match = re.search(CLASS_RE.format(name=name), source, re.MULTILINE)
    # Fall back to the first controller class of the file
    return match or re.search(CLASS_RE.format(name=r'\w+') + r'[ \t]+AbstractSDC\b', source, re.MULTILINE)


def _jsdoc_before(prefix):
    """Body of the ``/** ... */`` block that ends directly before the class (only whitespace between)."""
    prefix = prefix.rstrip()
    start = prefix.rfind('/**')
    if not prefix.endswith('*/') or start < 0 or '*/' in prefix[start + 3:-2]:
        return None
    return prefix[start + 3:-2]


def controller_doc(file, tag):
    """The text of the JSDoc block directly above the controller class, without the ``*`` gutter."""
    if not file:
        return None
    with open(file) as f:
        source = f.read()
    match = _class_match(source, tag)
    doc = _jsdoc_before(source[:match.start()]) if match else None
    if doc is None:
        return None
    lines = [re.sub(r'^\s*\* ?', '', l) for l in doc.splitlines()]
    return textwrap.dedent('\n'.join(lines)).strip() or None


def add_controller_doc(file, tag, doc):
    """
    Inserts ``doc`` as JSDoc block directly above the controller class in ``file``.

    :return: ``True`` if the file was changed
    """
    with open(file) as f:
        source = f.read()
    match = _class_match(source, tag)
    if not match or _jsdoc_before(source[:match.start()]) is not None:
        return False
    indent = match.group(1)
    doc = textwrap.dedent(doc).strip().replace('*/', '*\\/')
    block = [f'{indent}/**'] + [f'{indent} * {l}'.rstrip() for l in doc.splitlines()] + [f'{indent} */']
    with open(file, 'w') as f:
        f.write(source[:match.start()] + '\n'.join(block) + '\n' + source[match.start():])
    return True


def _read(file):
    try:
        with open(file) as f:
            return f.read()
    except (OSError, TypeError):
        return ''


def click_handlers(*sources):
    """The method names in the ``sdc_click`` attributes of ``sources`` (templates, JS code), in order."""
    handlers = []
    for source in sources:
        for match in SDC_CLICK_RE.finditer(source or ''):
            handlers += [h for h in match.group(1).split() if h not in handlers and re.fullmatch(r'[\w$]+', h)]
    return handlers


def method_doc(source, name):
    """The JSDoc text directly above the method ``name`` in ``source`` (without the ``*`` gutter) or ``None``."""
    match = re.search(METHOD_DOC_RE.format(name=re.escape(name)), source or '', re.DOTALL)
    if not match:
        return None
    lines = [re.sub(r'^\s*\* ?', '', l) for l in match.group(1).splitlines()]
    # @param / @return lines document the signature, not what the button does
    text = textwrap.dedent('\n'.join(lines)).split('\n@')[0]
    return text.strip() or None


def defines_method(source, name):
    """True if ``source`` contains a method definition ``name(...) {`` (class body style)."""
    return bool(re.search(rf'^[ \t]*(?:static[ \t]+)?(?:async[ \t]+)?{re.escape(name)}[ \t]*\([^)\n]*\)[ \t]*{{',
                          source or '', re.MULTILINE))


def project_click_handlers():
    """The ``sdc_click`` handlers of all templates of the installed apps (e.g. model list and detail templates)."""
    from django.apps import apps as django_apps
    sources = []
    for config in django_apps.get_app_configs():
        for root, _dirs, files in os.walk(os.path.join(config.path, 'templates')):
            sources += [_read(os.path.join(root, f)) for f in files if f.endswith('.html')]
    return click_handlers(*sources)


def template_source(view_class):
    """The source of the Django template (``template_name``) of the server view ``module.Class`` or ``''``."""
    try:
        module, name = view_class.rsplit('.', 1)
        template_name = getattr(getattr(importlib.import_module(module), name), 'template_name', None)
        if not template_name:
            return ''
        from django.template.loader import get_template
        return get_template(template_name).template.source
    except Exception:  # noqa: BLE001 - a view without a loadable template has no buttons to document
        return ''


def controller_actions(infos, template_handlers=None):
    """
    Adds ``actions`` (``{handler: doc}``) to every controller of ``infos``: the ``sdc_click`` handlers of its
    template and JS file, and the handlers of other templates (``template_handlers``, default: all templates of the
    installed apps) that its JS file defines, e.g. ``removeInstance`` of ``sdc-list-view`` used by the model list
    templates it shows. ``doc`` is the JSDoc of the method; a handler documented only in another controller file
    takes that doc.
    """
    if template_handlers is None:
        template_handlers = project_click_handlers()
    sources = {tag: _read(info.get('file')) for tag, info in infos.items()}
    for tag, info in infos.items():
        handlers = click_handlers(template_source(info.get('view_class') or ''), sources[tag])
        handlers += [h for h in template_handlers if h not in handlers and defines_method(sources[tag], h)]
        actions = {}
        for handler in handlers:
            doc = method_doc(sources[tag], handler)
            if doc is None:
                doc = next(filter(None, (method_doc(src, handler) for t, src in sources.items() if t != tag)), None)
            actions[handler] = doc
        info['actions'] = actions
    return infos


def method_line(file, name):
    """Line number of the method definition ``name`` in ``file`` (1-based) or ``None``."""
    source = _read(file)
    match = re.search(rf'^[ \t]*(?:static[ \t]+)?(?:async[ \t]+)?{re.escape(name)}[ \t]*\(', source, re.MULTILINE)
    return source.count('\n', 0, match.start()) + 1 if match else None


def controller_line(file, tag):
    """Line number of the controller class in ``file`` (1-based) or ``None``."""
    with open(file) as f:
        source = f.read()
    match = _class_match(source, tag)
    return source.count('\n', 0, match.start()) + 1 if match else None


def sdc_controllers():
    """
    ``{tag: {'app', 'view_class', 'url', 'file', 'doc', 'actions'}}`` for every SDC controller registered in the
    URL conf; ``file`` is the client controller JS file, ``doc`` its JSDoc text, ``actions`` the documentation of
    its button handlers (see ``controller_actions``).
    """
    infos = {}

    def walk(patterns, prefix):
        for p in patterns:
            if isinstance(p, URLResolver):
                walk(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern) and (p.name or '').startswith('scd_view_'):
                view = getattr(p.callback, 'view_class', None)
                if view is None:
                    continue
                tag = convert_to_tag_name(view.__name__)
                infos[tag] = {
                    'app': view.__module__.split('.')[0],
                    'view_class': f'{view.__module__}.{view.__name__}',
                    'url': '/' + prefix + str(p.pattern),
                }

    walk(get_resolver().url_patterns, '')
    for tag, info in infos.items():
        info['file'] = controller_js_file(info['app'], tag, info['url'])
        info['doc'] = controller_doc(info['file'], tag)
    return controller_actions(infos)
