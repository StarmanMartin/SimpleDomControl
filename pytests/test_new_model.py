
import subprocess

from pytests.utils import are_dir_trees_equal


def     test_new_model(init_project_with_app):
    subprocess.run(['python', 'manage.py', 'sdc_new_model', '-a', 'test_app_one', '-m', 'TestOneModel'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    subprocess.run(['python', 'manage.py', 'sdc_new_model', '-a', 'test_app_one', '-m', 'TestTwoModel'], stdout=subprocess.PIPE, cwd=init_project_with_app)
    dir1 = init_project_with_app
    dir2 = './pytests/expections/test_new_model/test_django_project'


    assert are_dir_trees_equal(dir1, dir2) == []