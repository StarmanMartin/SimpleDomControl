import re
import subprocess
import sys
import json

from pytests.utils import are_dir_trees_equal


def test_new_model(init_project_with_app):
    subprocess.run([sys.executable, 'manage.py', 'sdc_new_model', '-a', 'test_app_one', '-m', 'TestOneModel'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    subprocess.run([sys.executable, 'manage.py', 'sdc_new_model', '-a', 'test_app_one', '-m', 'TestTwoModel'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    dir1 = init_project_with_app
    dir2 = './pytests/expections/test_new_model/test_django_project'

    assert are_dir_trees_equal(dir1, dir2) == []

def test_model_list(init_project_with_app):
    subprocess.run([sys.executable, 'manage.py', 'sdc_new_model', '-a', 'test_app_one', '-m', 'TestOneModel'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    subprocess.run([sys.executable, 'manage.py', 'sdc_new_model', '-a', 'test_app_one', '-m', 'TestTwoModel'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    result = subprocess.run([sys.executable, 'manage.py', 'sdc_get_model_infos'], stdout=subprocess.PIPE, cwd=init_project_with_app)

    text = re.sub('}[^}]+$', '}', result.stdout.decode("utf-8"))
    result = json.loads(text)['sdc_models']

    assert len(result) == 2
    assert result[0]['model_file_line'] == 15
    assert result[1]['model_file_line'] == 42
    assert result[0]['name'] == 'TestOneModel'
    assert result[0]['app'] == 'test_app_one'
    assert result[0]['create_form']['class'] == 'TestOneModelForm'
    assert result[0]['create_form']['line'] == 8

