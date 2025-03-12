import os
import shutil
import subprocess
import sys

from pytests.utils import are_dir_trees_equal


def test_init():
    try:
        shutil.copytree('./pytests/test_django_project(DUMMY)', './pytests/test_django_project')
        subprocess.run([sys.executable, 'manage.py', 'sdc_init'], stdout=subprocess.PIPE, cwd=(os.path.join(os.getcwd(), './pytests/test_django_project')))
        dir1 = './pytests/test_django_project'
        dir2 = './pytests/expections/test_init/test_django_project'


        assert are_dir_trees_equal(dir1, dir2) == []
    finally:
        shutil.rmtree('./pytests/test_django_project')