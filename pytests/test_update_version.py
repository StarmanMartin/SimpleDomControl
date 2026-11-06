import importlib.util
import os
import shutil

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location('update_version', os.path.join(ROOT, 'scripts', 'update_version.py'))
update_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_version)


@pytest.fixture
def repo(tmp_path):
    """A copy of the files the script changes."""
    for file in {t[0] for t in update_version.TARGETS}:
        os.makedirs(tmp_path / os.path.dirname(file), exist_ok=True)
        shutil.copy(os.path.join(ROOT, file), tmp_path / file)
    return tmp_path


def test_sets_the_version_everywhere(repo, capsys):
    old = update_version.current_version(repo)
    assert update_version.main(['9.8.7', '--yes'], root=repo) == 0
    assert update_version.current_version(repo) == '9.8.7'
    for file, pattern, kind in update_version.TARGETS:
        text = (repo / file).read_text()
        assert '9.8.7' in text, file
        assert old not in text, file
    assert '"sdc_client": "^9.8.7"' in (repo / 'sdc_core/template_files/package.json').read_text()
    assert 'Updated 7 file(s)' in capsys.readouterr().out


def test_client_version_and_dry_run(repo):
    before = {f: (repo / f).read_text() for f, *_ in update_version.TARGETS}
    assert update_version.main(['9.8.7', '--dry-run'], root=repo) == 0
    assert before == {f: (repo / f).read_text() for f, *_ in update_version.TARGETS}
    update_version.main(['9.8.7', '--client-version', '9.8.1', '--yes'], root=repo)
    package = (repo / 'package.json').read_text()
    assert '"version": "9.8.7"' in package and '"sdc_client": "^9.8.1"' in package
    assert 'sdc_client = ^9.8.1' in (repo / 'docs/snippets/js_deps.rst').read_text()
    assert 'simpledomcontrol==9.8.7' in (repo / 'sdc/__main__.py').read_text()


def test_invalid_version_and_missing_pattern(repo):
    with pytest.raises(SystemExit, match='Invalid version'):
        update_version.main(['1.2', '--yes'], root=repo)
    (repo / 'docs/snippets/js_deps.rst').write_text('no version here')
    with pytest.raises(SystemExit, match='js_deps.rst: pattern'):
        update_version.main(['9.8.7', '--yes'], root=repo)
