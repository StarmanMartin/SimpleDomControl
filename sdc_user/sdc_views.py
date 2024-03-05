from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import RedirectURLMixin

from sdc_core.sdc_extentions.views import SDCView
from sdc_core.sdc_extentions.response import send_redirect, send_error
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings


class SdcLogin(SDCView, RedirectURLMixin):
    template_name='sdc_user/sdc/sdc_login.html'

    def post_api(self, request):
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None: # and user.is_email_confirmed:
                login(request, user)

                redirect_to = self.get_success_url()
                if redirect_to == self.request.path:
                    raise ValueError(
                        "Redirection loop for authenticated user detected. Check that "
                        "your LOGIN_REDIRECT_URL doesn't point to a login page."
                    )
                return send_redirect(url=redirect_to)

        msg = {
            'header' : 'Upss!',
            'msg':  "<ul>%s</ul>" % "\n".join(["<li>%s</li>" % v[0] for k, v in form.errors.items()])
             }
        return send_error(self.template_name, context={'form': form}, request=request, **msg)



    def get_content(self, request, *args, **kwargs):
        form = AuthenticationForm()
        self.next_page = request.GET.get('next')
        return render(request, self.template_name, {'form': form, 'redirect_field_name': self.redirect_field_name, 'next_page': self.next_page or settings.LOGIN_SUCCESS})

class SdcLogout(SDCView):
    template_name='sdc_user/sdc/sdc_logout.html'

    def post_api(self, request):
        logout(request)
        return send_redirect(url=f'/~{settings.LOGIN_CONTROLLER}')

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)

class SdcUserNavBtn(SDCView):
    template_name='sdc_user/sdc/sdc_user_nav_btn.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)