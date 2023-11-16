import os
import shutil
import subprocess
import uuid
import sys

import pytest


@pytest.fixture(scope='session')
def init_project():
    # Will be executed before the first test
    project_dir = os.path.join(os.getcwd(), 'pytests', uuid.uuid4().__str__())
    try:
        shutil.copytree('./pytests/test_django_project(DUMMY)', project_dir)
        subprocess.run([sys.executable, 'manage.py', 'sdc_init'], cwd=project_dir)
        yield project_dir
    finally:
        # Will be executed after the last test
        shutil.rmtree(project_dir)


@pytest.fixture(scope='session')
def init_project_with_app():
    # Will be executed before the first test
    project_dir = os.path.join(os.getcwd(), 'pytests', uuid.uuid4().__str__())
    try:
        shutil.copytree('./pytests/test_django_project(DUMMY)', project_dir)
        subprocess.run([sys.executable, 'manage.py', 'sdc_init'], cwd=project_dir)
        subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_one'], stdout=subprocess.PIPE, cwd=(project_dir))
        subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_two'], stdout=subprocess.PIPE, cwd=(project_dir))
        yield project_dir
    finally:
        # Will be executed after the last test
        shutil.rmtree(project_dir)