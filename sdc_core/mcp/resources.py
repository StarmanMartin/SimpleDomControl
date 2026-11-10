"""
Resources of the MCP endpoint: the knowledge of ``sdc_teach`` (``sdc_core.skill_data``) and the OpenAPI description
of the REST API. They describe the application, not its data, so every valid token may read them.
"""
import json

import yaml

from sdc_core import skill_data


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


def list_resources():
    return _skill_resources() + [OPENAPI]


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
    elif uri == OPENAPI['uri']:
        from sdc_core.management.commands.sdc_open_api import build_openapi
        text = yaml.safe_dump(build_openapi(), sort_keys=False, default_flow_style=False, allow_unicode=True)
        return _contents(uri, 'application/yaml', text)
    raise UnknownResource(uri)


def _contents(uri, mime_type, text):
    return {'contents': [{'uri': uri, 'mimeType': mime_type, 'text': text}]}
