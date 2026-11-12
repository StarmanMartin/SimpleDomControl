"""Route of the MCP endpoint; include it with ``path('sdc_mcp/', include('sdc_core.mcp.urls'))``."""
from django.urls import path

from sdc_core.mcp.view import SdcMcpView

urlpatterns = [
    path('', SdcMcpView.as_view(), name='sdc_mcp'),
]
