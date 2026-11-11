"""
Consistency checks of an SDC project (``manage.py sdc_agent check``). Each check returns ``Problem``s with a
location, what is wrong and how to fix it. Only project code is checked, never installed packages.

Severities: ``error`` (breaks the app), ``warning`` (likely a bug), ``doc`` (missing documentation for ``sdc_teach``
and the AI assistant; reported, but does not fail the check unless ``--strict``).
"""
import os
import re
from dataclasses import dataclass
from typing import Optional

from django.urls import Resolver404, resolve

CONTENT_URL_RE = re.compile(r'''this\.contentUrl\s*=\s*['"`]([^'"`]+)['"`]''')
REGISTER_RE = re.compile(r'\bapp\.(register|registerGlobal)\s*\(')
# A method header inside a class body: "    name(args) {" (also async / static)
METHOD_RE = re.compile(r'^[ \t]+(?:static\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', re.M)
# Start of an event registration: this.events.unshift(…), this.events.push(…), this.addEvent(…)
EVENT_CALL_RE = re.compile(r'this\.(?:events\.(?:unshift|push)|addEvent)\s*\(')
OPEN, CLOSE = '([{', ')]}'


@dataclass
class Problem:
    severity: str
    file: Optional[str]
    line: Optional[int]
    message: str
    fix: str


def _read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except (OSError, TypeError):
        return ''


def _line(text, position):
    return text.count('\n', 0, position) + 1


def _matching(js, start):
    """Index after the bracket that closes the one at ``start`` (strings and comments are skipped roughly)."""
    depth, i, quote = 0, start, None
    while i < len(js):
        char = js[i]
        if quote:
            if char == '\\':
                i += 1
            elif char == quote:
                quote = None
        elif char in '\'"`':
            quote = char
        elif js.startswith('//', i):
            i = js.find('\n', i)
            if i == -1:
                return len(js)
        elif char in OPEN:
            depth += 1
        elif char in CLOSE:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(js)


def _arrow_bodies(segment):
    """``(position, body)`` of every arrow function in ``segment``."""
    for match in re.finditer(r'=>\s*', segment):
        start = match.end()
        if start < len(segment) and segment[start] == '{':
            end = _matching(segment, start)
        else:
            # Expression body: up to the next , ) } at the same depth
            depth, end = 0, start
            while end < len(segment):
                char = segment[end]
                if char in OPEN:
                    depth += 1
                elif char in CLOSE:
                    if depth == 0:
                        break
                    depth -= 1
                elif char == ',' and depth == 0:
                    break
                end += 1
        yield match.start(), segment[start:end]


def constructor_arrow_handlers(js):
    """Positions of event handlers registered in the constructor as arrow functions that use ``this``."""
    result = []
    methods = list(METHOD_RE.finditer(js))
    for i, method in enumerate(methods):
        if method.group(1) != 'constructor':
            continue
        body_end = methods[i + 1].start() if i + 1 < len(methods) else len(js)
        for call in EVENT_CALL_RE.finditer(js, method.end(), body_end):
            call_end = _matching(js, call.end() - 1)
            for position, body in _arrow_bodies(js[call.end():call_end]):
                if re.search(r'\bthis\b', body):
                    result.append(call.end() + position)
    return result


def _resolves(url):
    try:
        resolve(url.split('?')[0])
        return True
    except Resolver404:
        return False


def check_controller(controller, project):
    problems = []
    name, tag = controller.name, controller.tag
    if not controller.js:
        problems.append(Problem('warning', controller.view_file, controller.view_line,
                                f'<{tag}> has a server view but no client controller '
                                f'(controller/{name}/{name}.js)',
                                f'create it with `python manage.py sdc_agent new-controller {controller.app} {name}` '
                                f'in a fresh app, or add the JS file and its organizer import'))
        return problems
    js = _read(controller.js)
    if controller.organizer and controller.organizer_line is None:
        problems.append(Problem('error', controller.organizer, None,
                                f'<{tag}> is not imported in the app organizer, so the browser never registers it',
                                f'add `import {{}} from "./controller/{name}/{name}.js";`'))
    if not REGISTER_RE.search(js):
        problems.append(Problem('error', controller.js, None, f'<{tag}> is never registered',
                                'end the file with `app.register(<ClassName>);`'))
    match = CONTENT_URL_RE.search(js)
    expected = controller.url.split('<')[0].rstrip('/')
    if match and not match.group(1).rstrip('/').startswith(expected):
        problems.append(Problem('error', controller.js, _line(js, match.start()),
                                f'contentUrl "{match.group(1)}" does not match the view URL {controller.url}',
                                f'set this.contentUrl = "{expected}"'))
    if controller.template_name and controller.template is None:
        problems.append(Problem('error', controller.view_file, controller.view_line,
                                f'template "{controller.template_name}" of <{tag}> does not exist',
                                'create it or fix template_name'))
    for position in constructor_arrow_handlers(js):
        problems.append(Problem('error', controller.js, _line(js, position),
                                f'<{tag}>: an arrow function registered as event handler in the constructor gets '
                                f'the wrong `this` (SDC calls handlers on the controller instance of the page)',
                                'use `function () { this.method(); }` or a method name, or register it in '
                                'willShow()'))
    if not controller.documented:
        problems.append(Problem('doc', controller.js, None, f'<{tag}> has no JSDoc above its class',
                                'see `python manage.py sdc_prepare_teaching`'))
    return problems


def check_client_only(app, directory, project):
    """A JS controller without server view is fine (mixins, client-only); its contentUrl must resolve, though."""
    name = os.path.basename(directory)
    js_path = os.path.join(directory, f'{name}.js')
    js = _read(js_path)
    match = CONTENT_URL_RE.search(js)
    if match and match.group(1).startswith('/') and not _resolves(match.group(1)):
        return [Problem('error', js_path, _line(js, match.start()),
                        f'contentUrl "{match.group(1)}" has no Django view',
                        f'add the view and URL (`python manage.py sdc_agent new-controller {app} {name}` creates '
                        f'both for a new controller) or remove contentUrl for a client-only controller')]
    return []


def check_model(model, project):
    problems = []
    from django.utils.module_loading import import_string
    for key, path in model.forms.items():
        try:
            import_string(path)
        except ImportError as e:
            problems.append(Problem('error', model.file, model.line,
                                    f'{model.name}: SdcMeta {key} form "{path}" cannot be imported ({e})',
                                    'fix the dotted path in SdcMeta or create the form'))
    if not model.documented:
        problems.append(Problem('doc', model.file, model.line, f'model {model.name} has no docstring',
                                'see `python manage.py sdc_prepare_teaching`'))
    return problems


def run_checks(project):
    problems = []
    for controller in project.controllers:
        if controller.editable:
            problems += check_controller(controller, project)
    for app, directory in project.orphan_js:
        problems += check_client_only(app, directory, project)
    for model in project.models:
        if model.editable:
            problems += check_model(model, project)
    order = {'error': 0, 'warning': 1, 'doc': 2}
    return sorted(problems, key=lambda p: (order[p.severity], p.file or '', p.line or 0))
