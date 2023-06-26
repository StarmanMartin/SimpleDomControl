import os
import subprocess
from subprocess import PIPE

from pytests.utils import are_dir_trees_equal


def test_cc(init_project):
    subprocess.run(['python', 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_one'], stdout=PIPE, cwd=(init_project))
    dir1 = init_project
    dir2 = './pytests/expections/test_cc/test_django_project'

    assert are_dir_trees_equal(dir1, dir2) == []