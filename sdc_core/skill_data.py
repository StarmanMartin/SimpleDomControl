"""
The knowledge about the project that ``sdc_teach`` writes, for every channel that hands it to an AI model (the AI
assistant ``SDCAiConsumer``, the MCP endpoint, ...):

- the skill file (``SDC_AI_SKILL_FILE``; by default ``SDC_SKILL.assistant.md``, else ``SDC_SKILL.md``),
- the skill data (``SDC_AI_SKILL_DATA_FILE``, default ``SDC_SKILL.data.json``): the source of the index (one line
  per view, controller and model) and of ``describe`` (the details of one of them),
- the ``SDC_SKILL.json`` of the installed apps,
- hand-written files (``SDC_AI_ADDITIONAL_SKILL_FILE``).

Paths are relative to ``BASE_DIR``. Which of them the assistant uses is its own setting (``SDC_AI_SKILL_SOURCE``,
``SDC_AI_SKILL_MODE``); this module only reads them.
"""
import json
import logging
import os

from django.conf import settings
from django.core.signals import setting_changed

logger = logging.getLogger(__name__)

_UNSET = object()
_skill_data = _UNSET


def _reset_cache(**kwargs):
    global _skill_data
    _skill_data = _UNSET


# Tests that override settings read the files again
setting_changed.connect(_reset_cache)


def _base_path(path):
    return os.path.join(str(getattr(settings, 'BASE_DIR', '')), os.fspath(path))


def skill_file_path():
    """
    ``SDC_AI_SKILL_FILE`` relative to ``BASE_DIR``; by default ``SDC_SKILL.assistant.md`` (written by ``sdc_teach``
    for the assistant) if it exists, else ``SDC_SKILL.md``.
    """
    configured = getattr(settings, 'SDC_AI_SKILL_FILE', None)
    if configured:
        return _base_path(configured)
    assistant = _base_path('SDC_SKILL.assistant.md')
    return assistant if os.path.isfile(assistant) else _base_path('SDC_SKILL.md')


def skill_markdown():
    """The content of the skill file (``skill_file_path``), None if it does not exist."""
    path = skill_file_path()
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        return f.read()


def read_skill_data_file():
    """
    ``(data, None)`` with the content of ``SDC_AI_SKILL_DATA_FILE`` (default ``SDC_SKILL.data.json`` next to
    manage.py), or ``(None, problem)`` if it is missing, unreadable or has another format.
    """
    path = _base_path(getattr(settings, 'SDC_AI_SKILL_DATA_FILE', None) or 'SDC_SKILL.data.json')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return None, f'cannot read {path} ({e})'
    from sdc_core.management.commands.utils.teach_data import FORMAT
    if not isinstance(data, dict) or data.get('format') != FORMAT:
        return None, f'{path} has another format (run sdc_teach again)'
    return data, None


def skill_data():
    """
    The skill data (``read_skill_data_file``) or None, read once per process (with ``DEBUG`` for every call, so
    a new ``sdc_teach`` run applies without a restart).
    """
    global _skill_data
    if not settings.DEBUG and _skill_data is not _UNSET:
        return _skill_data
    data, _problem = read_skill_data_file()
    if not settings.DEBUG:
        _skill_data = data
    return data


def skill_index(data=_UNSET):
    """The index of the skill data (one line per view, controller and model), None without skill data."""
    data = skill_data() if data is _UNSET else data
    if data is None:
        return None
    from sdc_core.management.commands.utils.teach_markdown import render_index
    return render_index(data)


def describe(name, data=_UNSET):
    """
    ``(text, is_error)``: the full documentation of one view, controller tag or model of the skill data; None
    without skill data.
    """
    data = skill_data() if data is _UNSET else data
    if data is None:
        return None
    from sdc_core.management.commands.utils.teach_markdown import describe as describe_name
    text = describe_name(data, name)
    return text, text.startswith('Unknown name')


def app_skills(include_hidden=False):
    """
    ``{app: SDC_SKILL.json content}`` of the installed apps. Controllers marked ``@ai-hidden`` are left out unless
    ``include_hidden``: there is nothing to operate in them.
    """
    from sdc_core.management.commands.utils.teach_apps import load_app_skills
    skills = load_app_skills()
    if not include_hidden:
        for skill in skills.values():
            controllers = skill.get('controllers')
            if isinstance(controllers, dict):
                skill['controllers'] = {t: c for t, c in controllers.items()
                                        if not (isinstance(c, dict) and c.get('hidden'))}
    return skills


def additional_skills():
    """Contents of the files in ``SDC_AI_ADDITIONAL_SKILL_FILE``; missing files are logged and skipped."""
    paths = getattr(settings, 'SDC_AI_ADDITIONAL_SKILL_FILE', None) or []
    if isinstance(paths, (str, os.PathLike)):
        paths = [paths]
    contents = []
    for path in paths:
        path = _base_path(path)
        try:
            with open(path, encoding='utf-8') as f:
                contents.append(f.read().strip())
        except OSError as e:
            logger.warning(f'SDC_AI_ADDITIONAL_SKILL_FILE: cannot read {path}: {e}')
    return contents
