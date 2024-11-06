from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async

from main_test.models import Author
from sdc_core.sdc_extentions.views import SDCView, SdcGroupRequiredMixin, SdcLoginRequiredMixin
from django.shortcuts import render


class MainView(SdcLoginRequiredMixin, SDCView):
    template_name = 'main_test/sdc/main_view.html'
    raise_exception = True

    def create_author(self):
        Author.objects.create(name='XX FF', age=2)

    def call_echo(self, channel=None, **kwargs):
        self.create_author()
        return kwargs

    async def call_async_echo(self, channel=None, **kwargs):
        await database_sync_to_async(self.create_author)()
        return kwargs

    def call_no_response(self, channel=None, **kwargs):
        pass


    async def test_echo_call(self, channel=None, **kwargs):
        await channel.state_redirect({'link': '/logged-in'})
        return kwargs

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class AdminOnly(SdcGroupRequiredMixin, SDCView):
    staff_allowed = False
    template_name = 'main_test/sdc/admin_only.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class StaffAndAdmin(SdcGroupRequiredMixin, SDCView):
    template_name = 'main_test/sdc/staff_and_admin.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class EditorAndStaff(SdcGroupRequiredMixin, SDCView):
    group_required = ['Editor']
    template_name = 'main_test/sdc/editor_and_staff.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class EditorNoStaff(SdcGroupRequiredMixin, SDCView):
    staff_allowed = False
    group_required = ['Editor']

    template_name = 'main_test/sdc/editor_no_staff.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class LoggedIn(SDCView):
    template_name = 'main_test/sdc/logged_in.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class Error404(SDCView):
    template_name='main_test/sdc/error_404.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)