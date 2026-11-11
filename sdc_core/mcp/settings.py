"""
Settings of the MCP endpoint (``SDC_MCP``, a dict; missing keys use ``DEFAULTS``):

- ``enabled``: the endpoint answers only if True (otherwise 404)
- ``models``: ``'__all__'`` or a list of SdcModel names that MCP clients may use at all; a model with
  ``SdcMeta.mcp = False`` is never exposed. Which of them a client really reaches depends on its token.
- ``max_records``: the most records ``model_load`` returns per call
- ``name``: the server name shown to MCP clients (default: the name of the project directory)
- ``instructions``: knowledge of ``sdc_teach`` in the server instructions: ``'models'`` (default: only the data
  models of the index; views matter only for the browser assistant), ``'index'`` (the whole index incl. the URL
  guide and the views) or ``'none'``. Details are always available through ``describe`` and the resources.
"""
from django.conf import settings

from sdc_core.sdc_extentions.models import all_models

DEFAULTS = {
    'enabled': False,
    'models': '__all__',
    'max_records': 50,
    'name': None,
    'instructions': 'models',
}


def mcp_settings():
    return DEFAULTS | (getattr(settings, 'SDC_MCP', None) or {})


def server_name():
    name = mcp_settings()['name']
    if name:
        return str(name)
    base = getattr(settings, 'BASE_DIR', None)
    return str(getattr(base, 'name', None) or 'sdc')


def exposed_models():
    """Names of the SdcModels that ``SDC_MCP['models']`` exposes, without those with ``SdcMeta.mcp = False``."""
    configured = mcp_settings()['models']
    models = all_models()
    if configured in (None, '__all__', '*'):
        names = list(models.keys())
    else:
        names = [models[name].__name__ for name in configured if name in models]
    return sorted((name for name in names if getattr(models[name].SdcMeta, 'mcp', True) is not False),
                  key=str.lower)
