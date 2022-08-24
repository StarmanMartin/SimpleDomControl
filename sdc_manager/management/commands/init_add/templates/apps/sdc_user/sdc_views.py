from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from sdc_tools.django_extension.response import send_success, send_redirect, send_error, sdc_link_factory, \
    send_controller
from sdc_tools.django_extension.views import SDCView
from django.shortcuts import render
from django.utils.translation import gettext as _f
from django.utils.translation import gettext_lazy as _

from sdc_user.email_handler import run_email_task
from sdc_user.form import CustomUserCreationForm, PasswordResetForm, CustomEditForm, LoginForm
from sdc_user.models import EmailLink


def get_next(request, default=None, next_next_default:str=None):
    next_val = request.POST.get('next', request.GET.get('next', default))
    if next_val is None:
        return {'is_next': False, 'next': next_val}
    if request.method.lower().startswith('get'):
        get_values = request.GET.copy()
        if '_method' in get_values:
            del get_values['_method']
        if 'VERSION' in get_values:
            del get_values['VERSION']
        if 'next_next' in get_values:
            del get_values['next_next']
        next_next = request.GET.get('next_next', next_next_default)
        if next_next is None and 'next' in get_values:
            del get_values['next']
        elif next_next is None :
            get_values['next'] = next_next_default
        next_val = sdc_link_factory(next_val, get_values)

    return {'is_next': True, 'next': next_val}

class LoginView(SDCView):
    template_name='sdc_user/sdc/login_view.html'

    form = LoginForm

    def post(self, request, *args, **kwargs):
        form = self.form(request=request, data=request.POST)
        context = get_next(request, 'main-view')
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
                                        msg="%s: %s" % (_f('Login succeeded'), user.email))
                else:
                    return send_redirect(url=context['next'], header=_f('Login success'),
                                         pk=user.pk,
                                         msg="%s: %s" % (_f('Login succeeded'), user.email))

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

class UserManager(SDCView):
    template_name='sdc_user/sdc/user_manager.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class UserRegister(LoginRequiredMixin, SDCView):
    raise_exception = True
    template_name = 'sdc_user/sdc/user_register.html'

    def prepare_form(self, ses_opt: dict, form: CustomUserCreationForm):
        if ses_opt is None:
            return form

        if ses_opt['email-fixed']:
            del form.fields['email']

        return form

    def prepare_sesssion(self, request):
        ses_opt = request.session.get('user_register_edit', None)
        return ses_opt

    def post_api(self, request, *args, **kwargs):
        ses_opt = self.prepare_sesssion(request)
        next = 'login-view'

        form = self.prepare_form(ses_opt, CustomUserCreationForm(request.POST))
        next = get_next(request, next)
        is_login = str(request.POST.get('is_login', '0'))
        context = {'form': form, 'next': next, 'is_login': is_login}
        if form.is_valid():
            if ses_opt is not None and ses_opt['email-fixed']:
                form.instance.email = ses_opt['email']
                form.instance.is_email_confirmed = True
            form.save()

            if ses_opt is None or not ses_opt['email-fixed']:
                form.instance.send_confirm_email(request)

            if is_login == '1':
                login(request, form.instance)
            if ses_opt is not None:
                del request.session['create_edit']

            return send_redirect(url=next['next'], header=_f('Registration success'),
                                 login=is_login == '1')

        return send_error(self.template_name, status=403, request=request, context=context,
                          header=_f('Registration Error'),
                          msg=_f('Please check you details!'))

    def get_content(self, request, *args, **kwargs):
        ses_opt = self.prepare_sesssion(request)
        is_login = str(request.GET.get('is_login', '0'))
        next = 'login-view'
        if ses_opt is not None:
            next = ses_opt.get('next', next)

        context = get_next(request, next)
        context['form'] = self.prepare_form(ses_opt, CustomUserCreationForm())
        context['is_login'] = is_login

        return render(request, self.template_name, context)


class UserInfo(SDCView):
    template_name='sdc_user/sdc/user_info.html'

    def get_content(self, request, *args, **kwargs):
        context = get_next(request)
        context['header'] = _(request.GET.get('header', 'Upps!!'))
        context['msg'] = _(request.GET.get('msg', 'Lost the message!'))
        return render(request, self.template_name, context)

class UserConfirmEmail(SDCView):
    template_name='sdc_user/sdc/user_info.html'

    def get_content(self, request, *args, **kwargs):
        key = kwargs.get('key', '')
        context = {'msg': _('Unbekannter Fehler'),
                   'header': _('Upps!!')}
        try:
            linkObj = EmailLink.objects.get(email_confirm_link=key)
            try:
                context = run_email_task(linkObj, request)
            except TimeoutError as e:
                context['header'] = _('Upps!!')
                context['msg'] = e.__str__()

            if 'controller' in context:
                return send_controller(context['controller'])

        except Exception as e:
            context['header'] = _('Upps!!')
            context['msg'] = _('Link is not correct!!')
        return render(request, self.template_name, context)

class UserLogout(SDCView):
    template_name='sdc_user/sdc/user_logout.html'

    def post(self, request, *args, **kwargs):
        uname = request.user.email
        logout(request)
        next = get_next(request, 'start-view')
        if next['is_next']:
            return send_redirect(url=next['next'], header=_f('Logout success'),
                             msg="%s: %s" % (_f('You are successfully logout:'), uname))

        return send_success()

    def get_content(self, request, *args, **kwargs):
        context = get_next(request)
        return render(request, self.template_name, context=context)

class UserPasswordForgotten(SDCView):
    template_name='sdc_user/sdc/user_password_forgotten.html'

    def post_api(self, request, *args, **kwargs):
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request=request)
            return send_redirect('user-info',
                                 link_data={'header': 'Email sent',
                                            'msg': 'We have sent you an email to reset your password'})

        return send_error(self.template_name, status=403, request=request, context={'form': form},
                          header=_f('Upps!!'),
                          msg=_f('Please check the entered email.'))

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': PasswordResetForm()})

class UserPasswordReset(SDCView):
    template_name='sdc_user/sdc/user_password_reset.html'

    def prepare_sesssion(self, request):
        ses_opt = request.session.get('reset_password', None)
        if ses_opt is None:
            return ses_opt

        ses_opt['link'] = EmailLink.objects.get(pk=ses_opt['link'])
        return ses_opt

    def post_api(self, request, *args, **kwargs):
        ses_opt = self.prepare_sesssion(request)
        if ses_opt is None:
            raise PermissionDenied()

        form = SetPasswordForm(ses_opt['link'].user, data=request.POST)

        if form.is_valid():
            form.save()
            return send_redirect('user-info',
                                 link_data={'header': 'Password changed',
                                            'msg': 'We have reset your password'})

        return send_error(self.template_name, status=403, request=request, context={'form': form},
                          header=_f('Upps!!'),
                          msg=_f('Please check your details.'))


    def get_content(self, request, *args, **kwargs):
        ses_opt = self.prepare_sesssion(request)
        if ses_opt is None:
            raise PermissionDenied()

        return render(request, self.template_name, {'form': SetPasswordForm(ses_opt['link'].user)})

class UserChangePassword(LoginRequiredMixin, SDCView):
    template_name='sdc_user/sdc/user_change_password.html'
    raise_exception = True

    def post_api(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user, data=request.POST)
        context = get_next(request)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            if context['is_next']:
                return send_redirect(url=context['next'], header=_f('Password successfully changed'),
                                     msg=_f('Your password has been changed'))

            return send_success()

        context['form'] = form
        return send_error(self.template_name, status=403, request=request, context={'form': form},
                          header=_f('Upps!!'),
                          msg=_f('Please check your details.'))

    def get_content(self, request, *args, **kwargs):
        context = get_next(request)
        context['form'] = PasswordChangeForm(request.user)
        return render(request, self.template_name, context)

class UserEdit(LoginRequiredMixin, SDCView):
    template_name='sdc_user/sdc/user_edit.html'
    raise_exception = True

    def post_api(self, request, *args, **kwargs):
        form = CustomEditForm(instance=request.user, data=request.POST)
        context = get_next(request)
        context['form'] = form
        if form.is_valid():
            email_has_changed = form.prepare_save(request)
            form.save()
            msg = ''
            if email_has_changed:
                msg = 'Please confirm your new email.'
                if context['is_next']:
                    return send_redirect(url=context['next'],
                                         header=_f('Successfully saved'),
                                         msg=_f(msg))


            return send_success(request=request, context=context,
                                header=_f('Successfully saved'),
                                msg=_f(msg))

        return send_error(self.template_name, status=403, request=request, context=context,
                          header=_f('Upps!!'),
                          msg=_f('Please check your details.'))

    def get_content(self, request, *args, **kwargs):
        form = CustomEditForm(request.user)
        context = get_next(request)
        context['form'] = form
        return render(request, self.template_name, context=context)