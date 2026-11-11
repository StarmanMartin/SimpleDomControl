"""
The agent kit of a project (projects/agents.architecture.md, section 2): ``AGENTS.md``, ``CLAUDE.md`` and the skills
in ``.claude/skills/``, written from ``sdc_core/template_files/agent_kit`` by ``sdc_init`` and
``manage.py sdc_agent kit install|update|check``.

The manifest ``.claude/skills/.sdc-kit.json`` records for every file the hash of the template it was written from
(``source``) and of the written content (``written``). ``update`` replaces files that were not edited since and
keeps edited ones; the generated block of ``AGENTS.md`` is always rewritten, the rest of it is kept.
"""
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parent.parent / 'template_files' / 'agent_kit'
MANIFEST = Path('.claude') / 'skills' / '.sdc-kit.json'
BLOCK_START = '<!-- sdc:generated:start'
BLOCK_END = '<!-- sdc:generated:end -->'
CLAUDE_IMPORT = '@AGENTS.md'


@dataclass
class KitResult:
    written: list = field(default_factory=list)
    kept: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _target(template):
    """``AGENTS.md`` / ``CLAUDE.md`` stay in the project root, ``skills/x`` goes to ``.claude/skills/x``."""
    relative = template.relative_to(KIT_DIR)
    if relative.parts[0] == 'skills':
        return Path('.claude') / relative
    return relative


def templates():
    """``{target path: template text}`` of the kit."""
    return {_target(path): path.read_text(encoding='utf-8')
            for path in sorted(KIT_DIR.rglob('*')) if path.is_file()}


def generated_block(project=None):
    """The project-specific part of AGENTS.md (apps, controllers, models); a pointer when the map is unavailable."""
    lines = []
    if project is not None:
        apps = project.project_apps()
        for app in apps:
            controllers = [c.tag for c in project.controllers if c.app == app]
            models = [m.name for m in project.models if m.app == app]
            parts = []
            if controllers:
                parts.append(f'{len(controllers)} controller(s)')
            if models:
                parts.append('models ' + ', '.join(models))
            lines.append(f'- `{app}`: ' + ('; '.join(parts) or 'no SDC parts yet'))
    if not lines:
        lines = ['- No project apps with SDC controllers or models yet.']
    return ('## This project\n\n' + '\n'.join(lines) +
            '\n\nDetails: `python manage.py sdc_agent overview`.\n')


def _with_block(text, block):
    """``text`` with the content between the generated-block markers replaced by ``block``."""
    start = text.find(BLOCK_START)
    end = text.find(BLOCK_END)
    if start == -1 or end == -1 or end < start:
        return text.rstrip('\n') + '\n\n' + _block_markers(block)
    head_end = text.index('\n', start) + 1
    return text[:head_end] + block + text[end:]


def _block_markers(block):
    return (f'{BLOCK_START} (rewritten by `python manage.py sdc_agent kit update`; edit outside this block) -->\n'
            f'{block}{BLOCK_END}\n')


def _render(target, text, block):
    return _with_block(text, block) if str(target) == 'AGENTS.md' else text


def load_manifest(root):
    path = Path(root) / MANIFEST
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except ValueError:
        return None


def _save_manifest(root, files):
    path = Path(root) / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'kit': 'sdc-agent-kit', 'files': files}, indent=1, sort_keys=True) + '\n',
                    encoding='utf-8')


def _write(root, target, text):
    path = Path(root) / target
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _merge_claude_md(existing):
    """An existing CLAUDE.md of the project gets the AGENTS.md import line once; the rest stays."""
    if CLAUDE_IMPORT in existing.split():
        return existing
    return f'{CLAUDE_IMPORT}\n\n{existing}' if existing.strip() else f'{CLAUDE_IMPORT}\n'


def install(root, project=None, force=False):
    """
    Writes the kit into the project ``root``. Existing files that are not from the kit are kept (``AGENTS.md``:
    the kit block is appended; ``CLAUDE.md``: the import line is added) unless ``force``.
    """
    result = KitResult()
    block = generated_block(project)
    files = {}
    for target, template in templates().items():
        path = Path(root) / target
        text = _render(target, template, block)
        if path.exists() and not force:
            existing = path.read_text(encoding='utf-8')
            if str(target) == 'CLAUDE.md':
                text = _merge_claude_md(existing)
            elif str(target) == 'AGENTS.md':
                text = _with_block(existing, block)
            else:
                result.kept.append(str(target))
                files[str(target)] = {'source': _hash(template), 'written': _hash(existing)}
                continue
        _write(root, target, text)
        result.written.append(str(target))
        files[str(target)] = {'source': _hash(template), 'written': _hash(text)}
    _save_manifest(root, files)
    return result


def update(root, project=None):
    """Brings an installed kit up to date; files edited in the project are kept and reported."""
    manifest = load_manifest(root)
    if manifest is None:
        return install(root, project)
    recorded = manifest.get('files', {})
    result = KitResult()
    block = generated_block(project)
    files = {}
    for target, template in templates().items():
        key = str(target)
        path = Path(root) / target
        entry = recorded.get(key)
        existing = path.read_text(encoding='utf-8') if path.exists() else None
        new_text = _render(target, template, block)
        if key == 'AGENTS.md' and existing is not None and entry and _hash(existing) != entry['written']:
            # Edited by hand: keep the edits, refresh only the generated block
            new_text = _with_block(existing, block)
        elif existing is not None and (entry is None or _hash(existing) != entry['written']):
            if key == 'CLAUDE.md':
                new_text = _merge_claude_md(existing)
            else:
                result.kept.append(key)
                files[key] = entry or {'source': _hash(template), 'written': _hash(existing)}
                continue
        if existing == new_text:
            result.unchanged.append(key)
        else:
            _write(root, target, new_text)
            result.written.append(key)
        files[key] = {'source': _hash(template), 'written': _hash(new_text)}
    _save_manifest(root, files)
    return result


def status(root):
    """``{'installed', 'outdated': [...], 'missing': [...], 'edited': [...]}`` of the kit in ``root``."""
    manifest = load_manifest(root)
    if manifest is None:
        return {'installed': False, 'outdated': [], 'missing': [], 'edited': []}
    recorded = manifest.get('files', {})
    outdated, missing, edited = [], [], []
    for target, template in templates().items():
        key = str(target)
        entry = recorded.get(key)
        path = Path(root) / target
        if not path.exists():
            missing.append(key)
            continue
        if entry is None or entry['source'] != _hash(template):
            outdated.append(key)
        if entry is not None and key not in ('AGENTS.md', 'CLAUDE.md') and \
                _hash(path.read_text(encoding='utf-8')) != entry['written']:
            edited.append(key)
    return {'installed': True, 'outdated': outdated, 'missing': missing, 'edited': edited}
