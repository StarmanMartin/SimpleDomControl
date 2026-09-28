import jwt
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.views import RedirectURLMixin
from django.http import HttpResponse, HttpRequest
from django.utils.html import escape

from sdc_core.sdc_extentions.views import SDCView, SdcLoginRequiredMixin
from sdc_core.sdc_extentions.response import send_redirect, send_error, send_success
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings

from sdc_user.forms import PasswordResetConfirmForm
from sdc_user.mails import (send_confirm_email, send_email_reset_email,
                            reset_token_fingerprint, confirm_token_fingerprint)


def _is_websocket(channel):
    # Server calls get the HttpRequest over HTTP and the consumer over WebSocket.
    return not isinstance(channel, HttpRequest) and isinstance(getattr(channel, 'scope', None), dict)


def _channel_user(channel):
    if _is_websocket(channel):
        return channel.scope.get('user')
    return getattr(channel, 'user', None)


def _channel_origin(channel):
    """Base URL of the site the request came from, or None (then settings.HOME_URL is used)."""
    if _is_websocket(channel):
        for name, value in channel.scope.get('headers', []):
            if name == b'origin':
                return value.decode('utf-8')
        return None
    return f"{channel.scheme}://{channel.get_host()}"


def _call_error(channel, msg):
    """An error result of a server call, shown with pushErrorMsg on the client."""
    if _is_websocket(channel):
        return {'is_error': True, 'header': 'Upss!', 'msg': msg}
    return send_error(msg=msg)


def _requires_confirmed_email(user):
    return getattr(settings, 'SDC_USER_REQUIRE_CONFIRMED_EMAIL', False) and not user.is_superuser \
        and not getattr(user, 'email_confirmed', True)


class SdcLogin(SDCView, RedirectURLMixin):
    template_name = 'sdc_user/sdc/sdc_login.html'

    def post_api(self, request):
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and _requires_confirmed_email(user):
                send_confirm_email(user, _channel_origin(request))
                return send_error(self.template_name, context={'form': form}, request=request, header='Upss!',
                                  msg=escape(_('Please confirm your e-mail address first. We have sent you a '
                                               'new confirmation e-mail.')))
            if user is not None:
                login(request, user)

                # Without a "next" parameter, go to settings.LOGIN_SUCCESS.
                self.next_page = getattr(settings, 'LOGIN_SUCCESS', '/')
                redirect_to = self.get_success_url()
                if redirect_to == self.request.path:
                    raise ValueError(
                        "Redirection loop for authenticated user detected. Check that "
                        "your LOGIN_REDIRECT_URL doesn't point to a login page."
                    )
                return send_redirect(url=redirect_to)

        msg = {
            'header': 'Upss!',
            'msg': "<ul>%s</ul>" % "\n".join(["<li>%s</li>" % escape(v[0]) for k, v in form.errors.items()])
        }
        return send_error(self.template_name, context={'form': form}, request=request, **msg)

    def get_content(self, request, *args, **kwargs):
        form = AuthenticationForm()
        self.next_page = request.GET.get('next')
        return render(request, self.template_name, {'form': form, 'redirect_field_name': self.redirect_field_name,
                                                    'next_page': self.next_page or settings.LOGIN_SUCCESS})


class SdcLogout(SDCView):
    template_name = 'sdc_user/sdc/sdc_logout.html'

    def post_api(self, request):
        logout(request)
        return send_redirect(url=f'/~{settings.LOGIN_CONTROLLER}')

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class SdcUserNavBtn(SDCView):
    template_name = 'sdc_user/sdc/sdc_user_nav_btn.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name, {'login_controller': settings.LOGIN_CONTROLLER})


class SdcConfirmEmail(SDCView):
    template_name = 'sdc_user/sdc/sdc_confirm_email.html'

    def get_content(self, request, token, *args, **kwargs):
        User = get_user_model()
        try:
            decoded_jwt = jwt.decode(token, settings.JWT['secret'], algorithms=[settings.JWT['algorithm']])
        except jwt.ExpiredSignatureError:
            # Expired: recover the user (ignoring exp) and send a fresh link.
            try:
                stale = jwt.decode(token, settings.JWT['secret'], algorithms=[settings.JWT['algorithm']],
                                   options={"verify_exp": False})
                user = User.objects.get(pk=stale['user'])
            except (jwt.InvalidTokenError, KeyError, User.DoesNotExist):
                return render(request, self.template_name, {'error': True, 'msg': _('No valid token.')})
            origin = f"{request.scheme}://{request.get_host()}"
            send_confirm_email(user, origin)
            return render(request, self.template_name,
                          {'error': True, 'msg': _('Your token has expired. A new one is on its way!')})
        except jwt.InvalidTokenError:
            return render(request, self.template_name, {'error': True, 'msg': _('No valid token.')})

        try:
            user = User.objects.get(pk=decoded_jwt['user'])
        except (KeyError, User.DoesNotExist):
            return render(request, self.template_name,
                          {'error': True, 'msg': _('Registration has been canceled. Please register new!')})

        # Single-use: reject a token that was already used or no longer matches.
        if decoded_jwt.get('fp') != confirm_token_fingerprint(user):
            return render(request, self.template_name, {'error': True, 'msg': _('No valid token.')})

        user.email_confirmed = True
        user.save()
        return render(request, self.template_name)


class SdcUser(SDCView):

    def get_user_id(self, channel):
        user = _channel_user(channel)
        if user is not None and user.is_authenticated:
            return user.id
        return None

    def get_content(self, request, *args, **kwargs):
        return HttpResponse('')


class SdcChangePassword(SdcLoginRequiredMixin, SDCView):
    # Shows the password form (SdcMeta.password_form) of the logged-in user.
    template_name = 'sdc_user/sdc/sdc_change_password.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class SdcPasswordForgotten(SDCView):
    template_name = 'sdc_user/sdc/sdc_password_forgotten.html'

    def send_email(self, channel, mail=None, **kwargs):
        User = get_user_model()  # gets the active AUTH_USER_MODEL

        username_field = User.USERNAME_FIELD
        try:
            user = User.objects.get(Q(**{username_field: mail}) | Q(email=mail))
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return _call_error(channel, _('User not found'))
        if not send_email_reset_email(user, _channel_origin(channel)):
            return _call_error(channel, _('The e-mail could not be sent. Please try again later.'))
        return {'msg': _('E-mail has been sent.')}

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class SdcResetPassword(SDCView):
    template_name = 'sdc_user/sdc/sdc_reset_password.html'

    def post_api(self, request):
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            User = get_user_model()  # gets the active AUTH_USER_MODEL
            token = form.cleaned_data["token"]
            password = form.cleaned_data["password"]
            # Decode the JWT; native exp enforces the 3-day expiry.
            try:
                decoded_jwt = jwt.decode(token, settings.JWT['secret'], algorithms=[settings.JWT['algorithm']])
            except jwt.ExpiredSignatureError:
                # Expired: recover the user (ignoring exp) and send a fresh link.
                try:
                    stale = jwt.decode(token, settings.JWT['secret'], algorithms=[settings.JWT['algorithm']],
                                       options={"verify_exp": False})
                    user = User.objects.get(id=stale.get("user"))
                except (jwt.InvalidTokenError, User.DoesNotExist):
                    return send_error(msg="Invalid or expired token")
                origin = f"{request.scheme}://{request.get_host()}"
                send_email_reset_email(user, origin)
                return send_error(msg=_('Your token has expired. A new one is on its way!'))
            except jwt.InvalidTokenError:
                return send_error(msg="Invalid or expired token")

            if decoded_jwt.get("type") != "reset":
                return send_error(msg="Invalid or expired token type")
            try:
                user = User.objects.get(id=decoded_jwt.get("user"))
            except User.DoesNotExist:
                return send_error(msg="Invalid or expired token")

            # Single-use: token is bound to the current password hash.
            if decoded_jwt.get("fp") != reset_token_fingerprint(user):
                return send_error(msg="Invalid or expired token")

            # Set the new password
            user.set_password(password)
            user.save()

            return send_success(msg=_('Password has been reset.'))

        return send_error(request=request, template_name=self.template_name, context={"form": form})

    def get_content(self, request, *args, **kwargs):
        token = request.GET.get("token")
        form = PasswordResetConfirmForm(initial={"token": token})
        return render(request, self.template_name, {"form": form})


class Register(SDCView):
    template_name='sdc_user/sdc/register.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)