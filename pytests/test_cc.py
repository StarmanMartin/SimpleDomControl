import json
import re
import sys
import subprocess
from subprocess import PIPE


from pytests.utils import are_dir_trees_equal


def test_cc(init_project):

    subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_one', '-m'], stdout=PIPE, cwd=(init_project))
    subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_two', '-m'], stdout=PIPE, cwd=(init_project))
    dir1 = init_project
    dir2 = './pytests/expections/test_cc/test_django_project'

    result = subprocess.run([sys.executable, 'manage.py', 'sdc_get_controller_infos'], stdout=subprocess.PIPE, cwd=init_project)

    text = re.sub('}[^}]+$', '}', result.stdout.decode("utf-8"))
    result = json.loads(text)['sdc_controller']['test_app_one']

    assert len(result) == 2
    assert result[0]['name'] in ['test_sdc_one', 'test_sdc_two']
    assert result[1]['name'] in ['test_sdc_one', 'test_sdc_two']

    assert are_dir_trees_equal(dir1, dir2) == []

