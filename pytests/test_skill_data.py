"""Tests of ``sdc_core.skill_data``: the knowledge of ``sdc_teach`` independent of the AI assistant's settings."""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.test import override_settings  # noqa: E402

from sdc_core import skill_data  # noqa: E402
from pytests.test_ai_consumer import _write_skill_data  # noqa: E402

NO_FILES = dict(SDC_AI_SKILL_FILE=None, SDC_AI_SKILL_DATA_FILE=None, SDC_AI_ADDITIONAL_SKILL_FILE=None)


def test_without_files(tmp_path):
    with override_settings(BASE_DIR=tmp_path, **NO_FILES):
        assert skill_data.skill_markdown() is None
        assert skill_data.skill_data() is None
        assert skill_data.skill_index() is None
        assert skill_data.describe('Author') is None
        assert skill_data.additional_skills() == []


def test_skill_file_prefers_the_assistant_file(tmp_path):
    (tmp_path / 'SDC_SKILL.md').write_text('# Skill')
    with override_settings(BASE_DIR=tmp_path, **NO_FILES):
        assert skill_data.skill_markdown() == '# Skill'
        (tmp_path / 'SDC_SKILL.assistant.md').write_text('# Assistant')
        assert skill_data.skill_markdown() == '# Assistant'
    with override_settings(BASE_DIR=tmp_path, **NO_FILES | {'SDC_AI_SKILL_FILE': 'SDC_SKILL.md'}):
        assert skill_data.skill_markdown() == '# Skill'


def test_index_and_describe(tmp_path):
    _write_skill_data(tmp_path / 'SDC_SKILL.data.json')
    with override_settings(BASE_DIR=tmp_path, **NO_FILES):
        assert '- `Author` — An author of books. Fields: name.' in skill_data.skill_index()
        text, is_error = skill_data.describe('<SDC-Login>')
        assert not is_error and '### `<sdc-login>`' in text
        text, is_error = skill_data.describe('logn')
        assert is_error and 'Close matches: sdc-login' in text


def test_skill_data_is_cached_without_debug(tmp_path):
    path = tmp_path / 'SDC_SKILL.data.json'
    _write_skill_data(path)
    with override_settings(BASE_DIR=tmp_path, DEBUG=False, **NO_FILES):
        first = skill_data.skill_data()
        path.unlink()
        assert skill_data.skill_data() is first
    with override_settings(BASE_DIR=tmp_path, DEBUG=True, **NO_FILES):
        assert skill_data.skill_data() is None


def test_app_skills_hide_hidden_controllers():
    skills = skill_data.app_skills()
    shown = skill_data.app_skills(include_hidden=True)
    assert set(skills) == set(shown)
    hidden = {tag for app in shown.values() for tag, c in (app.get('controllers') or {}).items()
              if isinstance(c, dict) and c.get('hidden')}
    assert hidden, 'the bundled apps have @ai-hidden controllers'
    assert not hidden & {tag for app in skills.values() for tag in (app.get('controllers') or {})}
