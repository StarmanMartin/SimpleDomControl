import json
import re
import sys
import subprocess
from subprocess import PIPE

from pytests.utils import are_dir_trees_equal


def test_cc(init_project):
    subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_one'], stdout=PIPE, cwd=(init_project))
    dir1 = init_project
    dir2 = './pytests/expections/test_cc/test_django_project'

    result = subprocess.run([sys.executable, 'manage.py', 'sdc_get_controller_infos'], stdout=subprocess.PIPE, cwd=init_project)

    text = re.sub('}[^}]+$', '}', result.stdout.decode("utf-8"))
    result = json.loads(text)['sdc_models']

    assert len(result) == 2
    assert result[0]['model_file_line'] == 15
    assert result[1]['model_file_line'] == 42
    assert result[0]['name'] == 'TestOneModel'
    assert result[0]['app'] == 'test_app_one'
    assert result[0]['create_form']['class'] == 'TestOneModelForm'
    assert result[0]['create_form']['line'] == 8

    assert are_dir_trees_equal(dir1, dir2) == []