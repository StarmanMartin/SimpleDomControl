import os
import shutil
import subprocess
import uuid
import sys

import pytest


def pytest_collection_finish(session):
    # Test modules that use Django in-process (test_ai_consumer, test_teach_markdown) set DJANGO_SETTINGS_MODULE to
    # SdcTest.settings when they are imported. Their settings are loaded by then; without removing the variable it is
    # inherited by the manage.py subprocesses of the project-generation tests, which would then run sdc_init, sdc_cc,
    # ... with the settings of SdcTest instead of the generated project.
    os.environ.pop('DJANGO_SETTINGS_MODULE', None)


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
        subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_one', '-m'], stdout=subprocess.PIPE, cwd=(project_dir))
        subprocess.run([sys.executable, 'manage.py', 'sdc_cc', '-a', 'test_app_one', '-c', 'test_sdc_two', '-m'], stdout=subprocess.PIPE, cwd=(project_dir))
        yield project_dir
    finally:
        # Will be executed after the last test
        shutil.rmtree(project_dir)