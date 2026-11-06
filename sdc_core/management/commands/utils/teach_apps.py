"""Per-app skill data (``SDC_SKILL.json``): written by ``sdc_teach --per-app``, read by every ``sdc_teach`` run."""
import json
import os

from django.apps import apps as django_apps

from sdc_core.management.commands.utils.teach_markdown import url_params

FILE_NAME = 'SDC_SKILL.json'


def app_skill_data(app, controllers, models):
    """
    The JSON content of one app: its controllers (with the documentation of their button actions) and SDC models
    with their documentation.

    :param controllers: ``{tag: info}`` of the app (see ``teach_controllers.sdc_controllers``)
    :param models: the app's entries of ``teach_models.sdc_models``
    """
    return {
        'app': app,
        'generator': 'manage.py sdc_teach --per-app',
        'controllers': {tag: {'doc': c.get('doc'), 'view_class': c.get('view_class'), 'url': c.get('url'),
                              'url_params': url_params(c.get('url')),
                              'actions': dict(sorted((c.get('actions') or {}).items()))}
                        for tag, c in sorted(controllers.items())},
        'models': {m['name']: {'doc': m.get('doc'), 'fields': m.get('fields') or []}
                   for m in sorted(models, key=lambda m: m['name'])},
    }


def write_app_skill(directory, data):
    path = os.path.join(directory, FILE_NAME)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    return path


def load_app_skills(app_configs=None):
    """``{app: data}`` of every installed app that ships an ``SDC_SKILL.json`` (unreadable files are skipped)."""
    skills = {}
    for config in app_configs if app_configs is not None else django_apps.get_app_configs():
        path = os.path.join(config.path, FILE_NAME)
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            skills[data.get('app') or config.label] = data
    return skills


def apply_app_skills(models, controllers, skills, prefer_json=True):
    """
    Sets the ``doc`` of models and controllers from the apps' ``SDC_SKILL.json``.

    :param prefer_json: ``True``: a JSON doc replaces the one from the source code; ``False``: it is only
                        used where the source code has none
    """
    def doc_of(app, kind, name):
        entry = (skills.get(app) or {}).get(kind, {}).get(name)
        return entry.get('doc') if isinstance(entry, dict) else None

    for m in models:
        doc = doc_of(m['app'], 'models', m['name'])
        if doc and (prefer_json or not m.get('doc')):
            m['doc'] = doc
    for tag, c in controllers.items():
        doc = doc_of(c['app'], 'controllers', tag)
        if doc and (prefer_json or not c.get('doc')):
            c['doc'] = doc
        # Button actions (sdc_click handlers) documented in the JSON
        entry = (skills.get(c['app']) or {}).get('controllers', {}).get(tag)
        json_actions = entry.get('actions') if isinstance(entry, dict) else None
        if isinstance(json_actions, dict):
            actions = c.setdefault('actions', {})
            for handler, doc in json_actions.items():
                if doc and (prefer_json or not actions.get(handler)):
                    actions[handler] = doc
