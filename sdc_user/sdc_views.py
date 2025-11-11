import jwt
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.views import RedirectURLMixin
from django.http import HttpResponse
from django.utils import timezone

from sdc_core.sdc_extentions.views import SDCView
from sdc_core.sdc_extentions.response import send_redirect, send_error, send_success
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from datetime import timedelta

from sdc_user.forms import PasswordResetConfirmForm
from sdc_user.mails import send_confirm_email, send_email_reet_email


class SdcLogin(SDCView, RedirectURLMixin):
    template_name = 'sdc_user/sdc/sdc_login.html'

    def post_api(self, request):
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:  # and user.is_email_confirmed:
                login(request, user)

                redirect_to = self.get_success_url()
                if redirect_to == self.request.path:
                    raise ValueError(
                        "Redirection loop for authenticated user detected. Check that "
                        "your LOGIN_REDIRECT_URL doesn't point to a login page."
                    )
                return send_redirect(url=redirect_to)

        msg = {
            'header': 'Upss!',
            'msg': "<ul>%s</ul>" % "\n".join(["<li>%s</li>" % v[0] for k, v in form.errors.items()])
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
        return render(request, self.template_name)


class SdcConfirmEmail(SDCView):
    template_name = 'sdc_user/sdc/sdc_confirm_email.html'

    def get_content(self, request, token, *args, **kwargs):
        try:
            decoded_jwt = jwt.decode(token, settings.JWT['secret'], algorithms=settings.JWT['algorithm'])
            min_iat = (timezone.now() - timedelta(days=3)).timestamp()
            try:
                user = get_user_model().objects.get(pk=decoded_jwt['user'])
            except get_user_model().DoesNotExist:
                return render(request, self.template_name,
                              {'error': True, 'msg': _('Registration has been canceled. Please register new!')})
            if min_iat > decoded_jwt['iat']:
                origin = f"{request.scheme}://{request.get_host()}"
                send_confirm_email(user, origin)
                return render(request, self.template_name, {'error': True, 'msg': _('Your token has expired. A new one is on its way!')})
            user.email_confirmed = True
            user.save()
        except jwt.exceptions.DecodeError:
            return render(request, self.template_name, {'error': True, 'msg': _('No valid token.')})

        return render(request, self.template_name)


class SdcUser(SDCView):

    def get_user_id(self, request):
        if request.user.is_authenticated:
            return request.user.id
        return None

    def get_content(self, request, *args, **kwargs):
        return HttpResponse('')


class SdcChangePassword(SDCView):
    template_name = 'sdc_user/sdc/sdc_change_password.html'

    def get_content(self, request, *args, **kwargs):
        return render(request, self.template_name)


class SdcPasswordForgotten(SDCView):
    template_name = 'sdc_user/sdc/sdc_password_forgotten.html'

    def send_email(self, request, mail):
        User = get_user_model()  # gets the active AUTH_USER_MODEL

        username_field = User.USERNAME_FIELD
        try:
            user = User.objects.get(Q(**{username_field: mail}) | Q(email=mail))
            origin = f"{request.scheme}://{request.get_host()}"
            send_email_reet_email(user, origin)
            return {'msg': _('E-mail has been sent.')}
        except get_user_model().DoesNotExist or User.MultipleObjectsReturned:
            return send_error(msg=_('User not found'))

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
            min_iat = (timezone.now() - timedelta(days=3)).timestamp()
            # Decode the JWT (you can adjust the decode options as needed)
            try:
                decoded_jwt = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                if decoded_jwt.get("type") != "reset":
                    return send_error(msg="Invalid or expired token type")

                user_id = decoded_jwt.get("user")
                user = User.objects.get(id=user_id)
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
                return send_error(msg="Invalid or expired token")

            if min_iat > decoded_jwt['iat']:
                origin = f"{request.scheme}://{request.get_host()}"
                send_email_reet_email(user, origin)
                return send_error(msg=_('Your token has expired. A new one is on its way!'))

            # Set the new password
            user.set_password(password)
            user.save()

            return send_success(msg=_('Password has been reset.'))

        return send_error(request=request, template_name=self.template_name, context={"form": form})

    def get_content(self, request, *args, **kwargs):
        token = request.GET.get("token")
        form = PasswordResetConfirmForm(initial={"token": token})
        return render(request, self.template_name, {"form": form})
