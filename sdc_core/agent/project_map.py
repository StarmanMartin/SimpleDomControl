"""
One map of an SDC project for ``manage.py sdc_agent``: its controllers (server view, URL, template, client JS,
SCSS, organizer entry) and SdcModels (fields, forms, documentation, MCP exposure). Built from the URL conf and the
model registry, like ``sdc_teach`` (``teach_controllers.sdc_controllers``, ``teach_models.sdc_models``).
"""
import importlib
import inspect
import os
from dataclasses import dataclass, field
from typing import Optional

from django.apps import apps as django_apps
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.module_loading import import_string

from sdc_core.management.commands.utils.teach_controllers import sdc_controllers
from sdc_core.management.commands.utils.teach_models import is_editable, sdc_models
from sdc_core.sdc_extentions.models import _SDC_META_DEFAULT

# SdcMeta keys that are no forms
_META_KEYS = set(_SDC_META_DEFAULT) - {'edit_form', 'create_form'} | {'mcp'}


@dataclass
class Controller:
    tag: str
    app: str
    name: str
    url: str
    view_class: str
    view_file: Optional[str] = None
    view_line: Optional[int] = None
    template: Optional[str] = None
    template_name: Optional[str] = None
    js: Optional[str] = None
    scss: Optional[str] = None
    organizer: Optional[str] = None
    organizer_line: Optional[int] = None
    documented: bool = False
    editable: bool = False


@dataclass
class Model:
    name: str
    app: str
    file: Optional[str]
    line: Optional[int]
    fields: list
    forms: dict
    documented: bool
    mcp: bool
    js_dir: Optional[str] = None
    editable: bool = False


@dataclass
class ProjectMap:
    root: str
    apps: list = field(default_factory=list)
    controllers: list = field(default_factory=list)
    models: list = field(default_factory=list)
    # JS controller directories of project apps without a server view in the URL conf: (app, directory)
    orphan_js: list = field(default_factory=list)

    def rel(self, path):
        """``path`` relative to the project root (absolute outside of it)."""
        if not path:
            return '-'
        real = os.path.realpath(path)
        root = os.path.realpath(self.root)
        return os.path.relpath(real, root) if real.startswith(root + os.sep) else path

    def project_apps(self):
        """Apps with code in the project (not installed packages) that have SDC controllers or models."""
        used = {c.app for c in self.controllers if c.editable} | {m.app for m in self.models if m.editable} | \
            {app for app, _ in self.orphan_js}
        return [app for app in self.apps if app in used]

    def library_apps(self):
        """``{app: number of controllers}`` of installed apps that are not part of the project."""
        result = {}
        for c in self.controllers:
            if not c.editable:
                result[c.app] = result.get(c.app, 0) + 1
        return dict(sorted(result.items()))

    def find(self, name):
        """Controllers and models matching a tag (``book-list`` / ``<book-list>``), snake name or model name."""
        key = name.strip().strip('<>').lower()
        controllers = [c for c in self.controllers if key in (c.tag, c.name, c.tag.replace('-', '_'))]
        models = [m for m in self.models if m.name.lower() == key]
        return controllers, models


def _app_path(app):
    try:
        return os.path.dirname(importlib.import_module(app).__file__)
    except (ImportError, TypeError):
        return None


def _in_project(path, root):
    path = os.path.realpath(path)
    return path.startswith(os.path.realpath(root) + os.sep) and 'site-packages' not in path.split(os.sep)


def _line_of(file, needle):
    try:
        with open(file, encoding='utf-8') as f:
            for number, line in enumerate(f, start=1):
                if needle in line:
                    return number
    except OSError:
        pass
    return None


def _controller(tag, info, root):
    app = info['app']
    url = info['url']
    parts = url.strip('/').split('/')
    name = parts[parts.index(app) + 1] if app in parts[:-1] else tag.replace('-', '_')
    controller = Controller(tag=tag, app=app, name=name, url=url, view_class=info['view_class'], js=info.get('file'),
                            documented=bool(info.get('doc')))
    try:
        view = import_string(info['view_class'])
        controller.view_file = inspect.getsourcefile(view)
        controller.view_line = inspect.getsourcelines(view)[1]
        controller.template_name = getattr(view, 'template_name', None)
    except (ImportError, OSError, TypeError):
        view = None
    if controller.template_name:
        try:
            controller.template = get_template(controller.template_name).origin.name
        except TemplateDoesNotExist:
            controller.template = None
    app_path = _app_path(app)
    if app_path:
        controller_dir = os.path.join(app_path, 'Assets', 'src', app, 'controller', name)
        scss = os.path.join(controller_dir, f'{name}.scss')
        controller.scss = scss if os.path.isfile(scss) else None
        organizer = os.path.join(app_path, 'Assets', 'src', app, f'{app}.organizer.js')
        if os.path.isfile(organizer):
            controller.organizer = organizer
            controller.organizer_line = _line_of(organizer, f'controller/{name}/{name}.js')
    controller.editable = is_editable(controller.view_file or controller.js, root)
    return controller


def _forms(model):
    meta = model.SdcMeta
    forms = {}
    for key in dir(meta):
        if key.startswith('_') or key in _META_KEYS:
            continue
        value = getattr(meta, key)
        if isinstance(value, str) and '.' in value or isinstance(value, type):
            forms[key.removesuffix('_form')] = value if isinstance(value, str) else \
                f'{value.__module__}.{value.__name__}'
    return forms


def _fields(model):
    result = []
    for f in list(model._meta.concrete_fields) + list(model._meta.many_to_many):
        if f.primary_key:
            continue
        if f.is_relation and f.related_model is not None:
            result.append(f'{f.name}→{f.related_model.__name__}{"*" if f.many_to_many else ""}')
        else:
            result.append(f.name)
    return result


def _model(info, root):
    model = info['model']
    try:
        line = inspect.getsourcelines(model)[1]
    except (OSError, TypeError):
        line = None
    app_path = _app_path(info['app'])
    js_dir = os.path.join(app_path, 'Assets', 'src', info['app'], 'models', model.__name__) if app_path else None
    return Model(name=model.__name__, app=info['app'], file=info['file'], line=line, fields=_fields(model),
                 forms=_forms(model), documented=bool(info['doc']),
                 mcp=getattr(model.SdcMeta, 'mcp', True) is not False,
                 js_dir=js_dir if js_dir and os.path.isdir(js_dir) else None,
                 editable=is_editable(info['file'], root))


def build(root=None):
    """The map of the running project (Django must be set up)."""
    root = str(root or getattr(settings, 'BASE_DIR', None) or os.getcwd())
    project = ProjectMap(root=root)
    for tag, info in sorted(sdc_controllers().items()):
        project.controllers.append(_controller(tag, info, root))
    project.models = [_model(info, root) for info in sdc_models()]

    known = {(c.app, c.name) for c in project.controllers}
    for config in django_apps.get_app_configs():
        app, app_path = config.label, config.path
        if not _in_project(app_path, root):
            continue
        project.apps.append(app)
        controller_root = os.path.join(app_path, 'Assets', 'src', app, 'controller')
        if os.path.isdir(controller_root):
            for name in sorted(os.listdir(controller_root)):
                if os.path.isdir(os.path.join(controller_root, name)) and (app, name) not in known:
                    project.orphan_js.append((app, os.path.join(controller_root, name)))
    return project
