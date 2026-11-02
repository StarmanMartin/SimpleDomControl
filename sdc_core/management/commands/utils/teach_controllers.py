"""Reads and writes the JSDoc comment of client controller classes (``class XController extends AbstractSDC``)."""
import importlib
import os
import re
import textwrap

from django.urls import URLPattern, URLResolver, get_resolver

from sdc_core.management.commands.init_add.utils import convert_to_tag_name, convert_to_title_camel_case

CLASS_RE = r'^([ \t]*)(?:export[ \t]+(?:default[ \t]+)?)?class[ \t]+{name}[ \t]+extends\b'


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


def controller_line(file, tag):
    """Line number of the controller class in ``file`` (1-based) or ``None``."""
    with open(file) as f:
        source = f.read()
    match = _class_match(source, tag)
    return source.count('\n', 0, match.start()) + 1 if match else None


def sdc_controllers():
    """
    ``{tag: {'app', 'view_class', 'url', 'file', 'doc'}}`` for every SDC controller registered in the URL
    conf; ``file`` is the client controller JS file, ``doc`` its JSDoc text.
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
    return infos
