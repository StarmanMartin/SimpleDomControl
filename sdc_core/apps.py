import os
import sys

from django.apps import AppConfig

# Defaults of Assets/.sdc_env (read by the Jest setup of `yarn sdc_test`)
SDC_ENV_DEFAULTS = {
    'JSON_DATA_DUMP': '"Assets/tests/dumps/test_data_dump.json"',
    'COPY_DEFAULT_DB': '1 # 0 for false or 1 for true',
    'DB_PYTHON_SCRIPT': '0 # Add path to pythonscript to prepare DB',
}


def _env_python(path):
    """The interpreter recorded in .sdc_python_env, or None."""
    try:
        with open(path, encoding='utf8') as f:
            text = f.read().strip()
    except OSError:
        return None
    if text.startswith('PYTHON='):
        return text[len('PYTHON='):].strip().strip('"')
    return None


def update_sdc_env_files(assets_dir, python=None):
    """
    Keeps ``Assets/.sdc_env`` and ``Assets/.sdc_python_env`` usable for the Jest tests without rewriting them on
    every start: missing keys of ``.sdc_env`` are appended (existing lines and comments stay), and
    ``.sdc_python_env`` is only written when it is missing or names an interpreter that does not exist any more.
    Returns the paths that were written.
    """
    python = python or sys.executable
    written = []
    env_path = os.path.join(assets_dir, '.sdc_env')
    existing = {}
    text = ''
    if os.path.exists(env_path):
        with open(env_path, encoding='utf8') as f:
            text = f.read()
        for line in text.splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                existing[key] = value
    missing = {key: value for key, value in SDC_ENV_DEFAULTS.items() if key not in existing}
    if missing:
        if text and not text.endswith('\n'):
            text += '\n'
        text += ''.join(f'{key}={value}\n' for key, value in missing.items())
        with open(env_path, 'w', encoding='utf8') as f:
            f.write(text)
        written.append(env_path)

    python_path = os.path.join(assets_dir, '.sdc_python_env')
    recorded = _env_python(python_path)
    if recorded is None or not os.path.isfile(recorded) or not os.access(recorded, os.X_OK):
        with open(python_path, 'w', encoding='utf8') as f:
            f.write(f'PYTHON="{python}"')
        written.append(python_path)
    return written


class SdcCoreConfig(AppConfig):
    name = 'sdc_core'

    def ready(self):
        from django.conf import settings
        import sdc_core.signals  # noqa: F401 (registers the signal receivers)

        assets_dir = os.path.join(str(getattr(settings, 'BASE_DIR', None) or os.getcwd()), 'Assets')
        if settings.DEBUG and os.path.isdir(assets_dir):
            update_sdc_env_files(assets_dir)
