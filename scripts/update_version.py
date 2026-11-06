#!/usr/bin/env python3
"""
Sets a new version of SimpleDomControl everywhere it is written down.

Server and client are released in lockstep, so the ``sdc_client`` dependency gets the same version unless
``--client-version`` says otherwise.

    python scripts/update_version.py              # asks for the new version
    python scripts/update_version.py 0.161.0      # shows the changes and asks for confirmation
    python scripts/update_version.py 0.161.0 --yes
    python scripts/update_version.py 0.161.0 --dry-run
    python scripts/update_version.py 0.161.0 --client-version 0.160.4

Run it from anywhere; paths are relative to the repository root. Afterwards run ``yarn install`` (yarn.lock) and
add a section to CHANGELOG.md; neither is changed by the script.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_RE = r'\d+\.\d+\.\d+(?:[-.]?(?:a|b|rc|alpha|beta|dev)\.?\d*)?'

# (file, pattern, kind): the pattern's group "v" is replaced; kind "version" = the package's own version,
# "client" = the sdc_client version it depends on
TARGETS = [
    ('pyproject.toml', rf'(?m)^version = "(?P<v>{VERSION_RE})"', 'version'),
    ('package.json', rf'(?m)^  "version": "(?P<v>{VERSION_RE})"', 'version'),
    ('package.json', rf'"sdc_client": "\^(?P<v>{VERSION_RE})"', 'client'),
    # The package.json of projects created by sdc_init and its snapshot in the init test
    ('sdc_core/template_files/package.json', rf'"sdc_client": "\^(?P<v>{VERSION_RE})"', 'client'),
    ('pytests/expections/test_init/test_django_project/package.json',
     rf'"sdc_client": "\^(?P<v>{VERSION_RE})"', 'client'),
    # Documentation
    ('docs/snippets/js_deps.rst', rf'sdc_client = \^(?P<v>{VERSION_RE})', 'client'),
    ('docs/build.rst', rf'``sdc_client`` (?P<v>{VERSION_RE})', 'client'),
    # Help text of the sdc command
    ('sdc/__main__.py', rf'simpledomcontrol==(?P<v>{VERSION_RE})', 'version'),
]


def current_version(root=ROOT):
    """The version in pyproject.toml."""
    with open(os.path.join(root, 'pyproject.toml'), encoding='utf-8') as f:
        match = re.search(TARGETS[0][1], f.read())
    if not match:
        raise SystemExit('No version found in pyproject.toml')
    return match.group('v')


def plan(root, version, client_version):
    """``[(file, old, new, count)]`` for every target; a target whose pattern is missing raises SystemExit."""
    changes = []
    for file, pattern, kind in TARGETS:
        path = os.path.join(root, file)
        if not os.path.isfile(path):
            raise SystemExit(f'{file} does not exist')
        with open(path, encoding='utf-8') as f:
            matches = list(re.finditer(pattern, f.read()))
        if not matches:
            raise SystemExit(f'{file}: pattern {pattern!r} not found - update TARGETS in {__file__}')
        new = version if kind == 'version' else client_version
        for old in sorted({m.group('v') for m in matches}):
            changes.append((file, kind, old, new, sum(m.group('v') == old for m in matches)))
    return changes


def apply(root, version, client_version):
    """Writes the new versions; returns the files that changed."""
    changed = []
    for file, pattern, kind in TARGETS:
        path = os.path.join(root, file)
        new = version if kind == 'version' else client_version
        with open(path, encoding='utf-8') as f:
            text = f.read()
        updated = re.sub(pattern, lambda m: m.group(0)[:m.start('v') - m.start()] + new
                         + m.group(0)[m.end('v') - m.start():], text)
        if updated != text:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(updated)
            if file not in changed:
                changed.append(file)
    return changed


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('version', nargs='?', help='The new version, e.g. 0.161.0 (asked for if missing)')
    parser.add_argument('--client-version', help='Version of the sdc_client dependency (default: the new version)')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would change')
    parser.add_argument('-y', '--yes', action='store_true', help='Do not ask for confirmation')
    ops = parser.parse_args(argv)

    old = current_version(root)
    version = ops.version
    if not version:
        version = input(f'Current version: {old}\nNew version: ').strip()
    client_version = ops.client_version or version
    for value, name in ((version, 'version'), (client_version, '--client-version')):
        if not re.fullmatch(VERSION_RE, value or ''):
            raise SystemExit(f'Invalid {name} {value!r}: use MAJOR.MINOR.PATCH, e.g. 0.161.0')

    changes = plan(root, version, client_version)
    print(f'SimpleDomControl {old} -> {version}' + (f' (sdc_client {client_version})'
                                                    if client_version != version else ''))
    for file, kind, current, new, count in changes:
        state = 'unchanged' if current == new else f'{current} -> {new}'
        print(f'  {file}: {kind} {state}' + (f' ({count}x)' if count > 1 else ''))
    if all(current == new for *_, current, new, _ in changes):
        print('Nothing to change.')
        return 0
    if ops.dry_run:
        print('Dry run: nothing written.')
        return 0
    if not ops.yes and input('Write these changes? [y/N] ').strip().lower() not in ('y', 'yes'):
        print('Cancelled.')
        return 1
    changed = apply(root, version, client_version)
    print(f'Updated {len(changed)} file(s). Next: yarn install (yarn.lock), a CHANGELOG.md section, and the same '
          f'version in SimpleDomControlClient/package.json.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
