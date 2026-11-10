"""
Snapshot of ``manage.py sdc_open_api`` for the models of ``SdcTest``
(``pytests/expections/test_open_api/SdcTest.openapi.yaml``). After an intended change of the OpenAPI description,
regenerate the snapshot: run ``sdc_open_api`` with ``SdcTest.settings`` and copy ``openapi.generated.yaml`` there.
"""
import os
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.core.management import call_command  # noqa: E402

SNAPSHOT = Path(__file__).parent / 'expections' / 'test_open_api' / 'SdcTest.openapi.yaml'


def test_open_api_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    call_command('sdc_open_api', stdout=open(os.devnull, 'w'))
    assert (tmp_path / 'openapi.generated.yaml').read_text() == SNAPSHOT.read_text()


def test_schema_module_is_the_source_of_the_command():
    from sdc_core.management.commands import sdc_open_api
    from sdc_core.sdc_extentions import schema
    assert sdc_open_api.generate_form_schema is schema.generate_form_schema
    assert sdc_open_api.generate_fields_schema is schema.generate_fields_schema
