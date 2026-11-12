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


@pytest.fixture(scope='module')
def django_test_db():
    """
    A fresh, migrated test database (in-memory SQLite of ``SdcTest.settings``) for the tests of one module that
    use Django in-process; the module sets ``DJANGO_SETTINGS_MODULE`` and calls ``django.setup()`` when imported.
    """
    from django.db import connection
    from django.test.utils import setup_test_environment, teardown_test_environment
    setup_test_environment()
    old_name = connection.creation.create_test_db(verbosity=0, autoclobber=True)
    try:
        yield
    finally:
        connection.creation.destroy_test_db(old_name, verbosity=0)
        teardown_test_environment()


@pytest.fixture
def db(django_test_db):
    """Runs the test in a transaction that is rolled back afterwards."""
    from django.db import transaction
    with transaction.atomic():
        yield
        transaction.set_rollback(True)


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