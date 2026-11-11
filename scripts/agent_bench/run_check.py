"""
Runs the check of one task inside a benchmark project: ``python run_check.py <task id> <project dir>``.
Prints one line ``RESULT <json>`` with ``{"passed": bool, "details": {...}}``.
"""
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(task_id, project):
    project = Path(project).resolve()
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(project))
    os.chdir(project)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'test_django_project.settings'
    try:
        import django
        django.setup()
        from tasks import BY_ID
        passed, details = BY_ID[task_id].check(project)
    except Exception as e:  # noqa: BLE001 - a crash of the project is a failed check
        passed, details = False, {'error': {'ok': False, 'detail': f'{e!r}\n{traceback.format_exc()[-1500:]}'}}
    print('RESULT ' + json.dumps({'passed': passed, 'details': details}, default=str))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
