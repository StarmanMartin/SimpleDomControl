import json
import re
import sys
import subprocess
import logging
from subprocess import PIPE

from pytests.utils import are_dir_trees_equal


def test_cc(init_project):
    subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_one'], stdout=PIPE, cwd=(init_project))
    subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_two'], stdout=PIPE, cwd=(init_project))
    dir1 = init_project
    dir2 = './pytests/expections/test_cc/test_django_project'

    result = subprocess.run([sys.executable, 'manage.py', 'sdc_get_controller_infos'], stdout=subprocess.PIPE, cwd=init_project)

    text = re.sub('}[^}]+$', '}', result.stdout.decode("utf-8"))
    result = json.loads(text)['sdc_controller']['test_app_one']

    assert len(result) == 2
    assert result[0]['name'] == 'test_sdc_one'
    assert result[1]['name'] == 'test_sdc_two'

    assert are_dir_trees_equal(dir1, dir2) == []

