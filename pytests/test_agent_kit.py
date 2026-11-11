"""
Tests of the agent kit (projects/agents.plan.md, M2): templates, install / update / check, and that every
``manage.py`` command line the kit shows to agents parses with the real command parsers.
"""
import os
import re
import shlex

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.core.management import get_commands, load_command_class  # noqa: E402

from sdc_core.agent import kit  # noqa: E402

SKILLS = ['sdc-ai-knowledge', 'sdc-api-mcp', 'sdc-controller', 'sdc-model', 'sdc-testing']


def _front_matter(text):
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    assert match, 'missing front matter'
    return dict(line.split(': ', 1) for line in match.group(1).splitlines())


def test_templates():
    files = kit.templates()
    assert {str(p) for p in files} >= {'AGENTS.md', 'CLAUDE.md'} | {f'.claude/skills/{s}/SKILL.md' for s in SKILLS}
    # Always loaded: keep it small (~4 characters per token)
    assert len(files[kit.Path('AGENTS.md')]) < 3600
    for skill in SKILLS:
        text = files[kit.Path('.claude/skills') / skill / 'SKILL.md']
        meta = _front_matter(text)
        assert meta['name'] == skill
        assert 30 < len(meta['description']) < 400
        assert len(text) < 9000, skill


def test_agents_md_lists_every_skill():
    agents = kit.templates()[kit.Path('AGENTS.md')]
    for skill in SKILLS:
        assert f'`{skill}`' in agents


def test_referenced_files_exist():
    files = {str(p) for p in kit.templates()}
    for target, text in kit.templates().items():
        for ref in re.findall(r'`(references/[\w.-]+\.md)`', text):
            assert str(target.parent / ref) in files, (target, ref)


def _command_lines():
    """Every `python manage.py …` invocation of the kit, split at `&&`, without comments and placeholders."""
    lines = set()
    for target, text in kit.templates().items():
        for match in re.finditer(r'python manage\.py ([^`\n]+)', text):
            for part in match.group(1).split('&&'):
                part = part.replace('python manage.py', '')
                part = re.sub(r'\s#.*$', '', part)            # comments in code blocks
                part = re.sub(r'\[[^\]]*\]', '', part)        # [optional] parts
                part = re.sub(r'<[^>]+>', 'x', part)          # <placeholders>
                part = part.replace('…', '').strip().rstrip('.;,)')
                if part:
                    lines.add((str(target), part))
    return sorted(lines)


@pytest.mark.parametrize('source, line', _command_lines())
def test_kit_commands_parse(source, line):
    args = shlex.split(line)
    name, args = args[0], args[1:]
    commands = get_commands()
    assert name in commands, f'{source}: unknown command {name}'
    parser = load_command_class(commands[name], name).create_parser('manage.py', name)
    try:
        parser.parse_args(args)
    except SystemExit:
        pytest.fail(f'{source}: `{line}` does not parse')


# ------------------------------------------------------------------ install / update / status

def test_install_update_status(tmp_path):
    result = kit.install(tmp_path)
    assert 'AGENTS.md' in result.written and '.claude/skills/sdc-model/SKILL.md' in result.written
    assert kit.status(tmp_path) == {'installed': True, 'outdated': [], 'missing': [], 'edited': []}
    agents = (tmp_path / 'AGENTS.md').read_text()
    assert '## This project' in agents and kit.BLOCK_END in agents

    # An edited skill is kept on update and reported; an untouched one would be replaced
    skill = tmp_path / '.claude/skills/sdc-model/SKILL.md'
    skill.write_text(skill.read_text() + '\nProject note.\n')
    assert kit.status(tmp_path)['edited'] == ['.claude/skills/sdc-model/SKILL.md']
    result = kit.update(tmp_path)
    assert '.claude/skills/sdc-model/SKILL.md' in result.kept and skill.read_text().endswith('Project note.\n')

    # Edits of AGENTS.md outside the generated block stay; the block is rewritten
    agents_path = tmp_path / 'AGENTS.md'
    agents_path.write_text('# My project rules\n\n' + agents_path.read_text().replace(
        '## This project', '## This project\n\nstale', 1))
    kit.update(tmp_path)
    text = agents_path.read_text()
    assert text.startswith('# My project rules') and 'stale' not in text

    # A newer template (simulated: other source hash) makes the kit outdated until update
    manifest = kit.load_manifest(tmp_path)
    manifest['files']['.claude/skills/sdc-testing/SKILL.md']['source'] = 'old'
    kit._save_manifest(tmp_path, manifest['files'])
    assert kit.status(tmp_path)['outdated'] == ['.claude/skills/sdc-testing/SKILL.md']
    kit.update(tmp_path)
    assert kit.status(tmp_path)['outdated'] == []


def test_install_keeps_existing_project_files(tmp_path):
    (tmp_path / 'CLAUDE.md').write_text('Use tabs.\n')
    (tmp_path / 'AGENTS.md').write_text('# Rules of this team\n')
    kit.install(tmp_path)
    assert (tmp_path / 'CLAUDE.md').read_text() == '@AGENTS.md\n\nUse tabs.\n'
    agents = (tmp_path / 'AGENTS.md').read_text()
    assert agents.startswith('# Rules of this team') and '## This project' in agents
    kit.update(tmp_path)
    assert (tmp_path / 'CLAUDE.md').read_text().count('@AGENTS.md') == 1


def test_generated_block_lists_project_apps():
    from sdc_core.agent.project_map import build
    block = kit.generated_block(build())
    assert '- `main_test`: 9 controller(s); models Author, Book, BookContent' in block
