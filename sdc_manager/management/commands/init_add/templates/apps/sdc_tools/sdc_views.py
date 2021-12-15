from django.shortcuts import render

from sdc_tools.django_extension.response import send_success
from sdc_tools.django_extension.views import SDCView


class NavView(SDCView):
    template_name='sdc_tools/sdc/nav_view.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class NavClient(SDCView):

    def get_content(self, request, *args, **kwargs):
        return send_success()

class ListMixin(SDCView):

    def get_content(self, request, *args, **kwargs):
        return send_success()

class GAlertMsg(SDCView):
    template_name='sdc_tools/sdc/g_alert_msg.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class ChangeSyncMixin(SDCView):

    def get_content(self, request, *args, **kwargs):
        return send_success()

class SearchController(SDCView):
    template_name='sdc_tools/sdc/search_controller.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class AutoSubmitMixin(SDCView):
    template_name='sdc_tools/sdc/auto_submit_mixin.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class GlobalDomEvents(SDCView):
    template_name='sdc_tools/sdc/global_dom_events.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)