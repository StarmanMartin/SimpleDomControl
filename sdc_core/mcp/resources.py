"""
Resources of the MCP endpoint: the knowledge of ``sdc_teach`` (``sdc_core.skill_data``), the OpenAPI description
of the REST API and the application's own files (``SDC_MCP['resources']``, ``sdc://app/<name>``; files that
are not UTF-8 text are served as base64 ``blob`` contents). They describe the
application, not its data, so every valid token may read them.
"""
import base64
import json
import logging
import mimetypes
import os
import re

import yaml
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from sdc_core import skill_data
from sdc_core.mcp.settings import mcp_settings

logger = logging.getLogger(__name__)
APP_PREFIX = 'sdc://app/'
APP_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


class UnknownResource(Exception):
    pass


def _skill_resources():
    resources = []
    if skill_data.skill_markdown() is not None:
        resources.append({'uri': 'sdc://skill', 'name': 'skill', 'title': 'Skill file of this website',
                          'description': 'Views, navigation and data models of this website (written by '
                                         'manage.py sdc_teach)',
                          'mimeType': 'text/markdown'})
    for app in sorted(skill_data.app_skills()):
        resources.append({'uri': f'sdc://skill/{app}', 'name': f'skill-{app}', 'title': f'Skill data of {app}',
                          'description': f'Controllers and data models of the app {app} (SDC_SKILL.json)',
                          'mimeType': 'application/json'})
    return resources


OPENAPI = {'uri': 'sdc://openapi', 'name': 'openapi', 'title': 'OpenAPI description of the REST API',
           'description': 'The REST API (sdc_api/) of the data models, with the privileges of every operation',
           'mimeType': 'application/yaml'}


def app_resources():
    """
    The configured application resources ``{name: {'uri', 'name', 'title', 'description', 'mimeType', 'path',
    'known_type'}}`` (``SDC_MCP['resources']``), in their order; ``ImproperlyConfigured`` for invalid entries.
    ``known_type`` is false when the type is neither configured nor guessable: such a file is listed as
    ``text/plain`` and, if it is not UTF-8 text, read as an ``application/octet-stream`` blob.
    """
    configured = mcp_settings().get('resources') or []
    if not isinstance(configured, (list, tuple)):
        raise ImproperlyConfigured("SDC_MCP['resources'] must be a list of {'name', 'path', ...}")
    result = {}
    for entry in configured:
        if not isinstance(entry, dict) or not isinstance(entry.get('name'), str) or \
                not APP_NAME_PATTERN.match(entry['name']) or not entry.get('path'):
            raise ImproperlyConfigured(f"SDC_MCP['resources']: invalid entry {entry!r} (needs a 'name' of letters, "
                                       f"digits, _ and - and a 'path')")
        if entry['name'] in result:
            raise ImproperlyConfigured(f"SDC_MCP['resources']: the name {entry['name']!r} is used twice")
        path = os.path.join(str(getattr(settings, 'BASE_DIR', '')), os.fspath(entry['path']))
        mime_type = entry.get('mimeType') or ('text/markdown' if path.endswith('.md') else
                                              mimetypes.guess_type(path)[0])
        result[entry['name']] = {'uri': APP_PREFIX + entry['name'], 'name': entry['name'],
                                 'title': entry.get('title') or entry['name'],
                                 'description': entry.get('description') or '', 'mimeType': mime_type or 'text/plain',
                                 'path': path, 'known_type': mime_type is not None}
    return result


_INTERNAL_KEYS = ('path', 'known_type')


def listed_app_resources():
    resources = []
    for resource in app_resources().values():
        if not os.path.isfile(resource['path']):
            logger.warning("MCP resource %s: the file does not exist", resource['uri'])
            continue
        resources.append({key: value for key, value in resource.items() if key not in _INTERNAL_KEYS})
    return resources


def list_resources():
    return _skill_resources() + listed_app_resources() + [OPENAPI]


def read_resource(uri):
    """The MCP ``resources/read`` result for ``uri``; ``UnknownResource`` if there is none."""
    if uri == 'sdc://skill':
        text = skill_data.skill_markdown()
        if text is not None:
            return _contents(uri, 'text/markdown', text)
    elif isinstance(uri, str) and uri.startswith('sdc://skill/'):
        skills = skill_data.app_skills()
        app = uri[len('sdc://skill/'):]
        if app in skills:
            return _contents(uri, 'application/json', json.dumps(skills[app], indent=1, ensure_ascii=False))
    elif isinstance(uri, str) and uri.startswith(APP_PREFIX):
        resource = app_resources().get(uri[len(APP_PREFIX):])
        if resource is not None and os.path.isfile(resource['path']):
            with open(resource['path'], 'rb') as file:
                data = file.read()
            try:
                return _contents(uri, resource['mimeType'], data.decode('utf-8'))
            except UnicodeDecodeError:
                mime_type = resource['mimeType'] if resource['known_type'] else 'application/octet-stream'
                return {'contents': [{'uri': uri, 'mimeType': mime_type,
                                      'blob': base64.b64encode(data).decode('ascii')}]}
    elif uri == OPENAPI['uri']:
        from sdc_core.management.commands.sdc_open_api import build_openapi
        text = yaml.safe_dump(build_openapi(), sort_keys=False, default_flow_style=False, allow_unicode=True)
        return _contents(uri, 'application/yaml', text)
    raise UnknownResource(uri)


def _contents(uri, mime_type, text):
    return {'contents': [{'uri': uri, 'mimeType': mime_type, 'text': text}]}
