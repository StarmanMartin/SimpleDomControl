from sdc_core.sdc_extentions.views import SDCView
from django.shortcuts import render



class TestSdcOne(SDCView):
    template_name='test_app_one/sdc/test_sdc_one.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)