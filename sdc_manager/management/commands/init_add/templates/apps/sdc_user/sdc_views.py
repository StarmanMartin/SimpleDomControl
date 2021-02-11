from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

from sdc_tools.django_extension.response import send_success, send_redirect, send_error, sdc_link_factory
from sdc_tools.django_extension.views import SDCView
from django.shortcuts import render
from django.utils.translation import ugettext as _f

def get_next(request, default=None, next_next_default:str=None):
    next_val = request.POST.get('next', request.GET.get('next', default))
    if request.method.lower().startswith('get'):
        get_values = request.GET.copy()
        del get_values['_method']
        del get_values['VERSION']
        if 'next_next' in get_values: del get_values['next_next']
        next_next = request.GET.get('next_next', next_next_default)
        if next_next is None:
            del get_values['next']
        else :
            get_values['next'] = next_next_default
        next_val = sdc_link_factory(next_val, get_values)

    return {'is_next': True, 'next': next_val}


class LoginView(SDCView):
    template_name='sdc_user/sdc/login_view.html'

    form = AuthenticationForm

    def post(self, request, *args, **kwargs):
        form = self.form(request=request, data=request.POST)
        context = get_next(request)
        context['form'] = form
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and user.is_email_confirmed:
                login(request, user)
                if not context['is_next']:
                    return send_success(self.template_name, context=context, request=request,
                                        header=_f('Login success'),
                                        pk=user.pk,
                                        msg="%s: %s" % (_f('Login succeeded'), user.username))
                else:
                    return send_redirect(url=context['next'], header=_f('Login success'),
                                         pk=user.pk,
                                         msg="%s: %s" % (_f('Login succeeded'), user.username))

            elif user is not None and not user.is_email_confirmed:
                user.send_confirm_email(request)
                return send_error(self.template_name, context=context, request=request, status=403,
                                  header=_f('Login failed'),
                                  msg=_f('Your email is not confirmed. We will send you a new link.'), )

        return send_error(self.template_name, context=context, request=request, status=403, header=_f('Login failed'),
                          msg=_f('Sorry, password or e-mail is not correct'), )

    def get_content(self, request, *args, **kwargs):
        context = get_next(request)
        context['form'] = self.form()
        return render(request, self.template_name, context)