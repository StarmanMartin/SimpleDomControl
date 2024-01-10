from django.shortcuts import render
from sdc_core.sdc_extentions.views import SDCView




class SdcNavigator(SDCView):
    template_name = 'sdc_tools/sdc/sdc_navigator.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class SdcListView(SDCView):
    template_name='sdc_tools/sdc/sdc_list_view.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class SdcModelForm(SDCView):
    template_name='sdc_tools/sdc/sdc_model_form.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class SdcDetailView(SDCView):
    template_name='sdc_tools/sdc/sdc_detail_view.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class SdcSearchView(SDCView):
    template_name='sdc_tools/sdc/sdc_search_view.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class SdcAlertMessenger(SDCView):
    template_name='sdc_tools/sdc/sdc_alert_messenger.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class SdcError(SDCView):
    template_name='sdc_tools/sdc/sdc_error.html'

    def get_content(self, request, code, *args, **kwargs):
        return render(request, self.template_name, {'code': code})

class SdcDummy(SDCView):
    template_name='sdc_tools/sdc/sdc_dummy.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)