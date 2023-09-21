from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.views import View
from functools import wraps
from sdc_core.sdc_extentions.response import send_redirect
from django.conf import settings

class SdcLoginRequiredMixin(LoginRequiredMixin):
    login_controller = None
    request = None

    def get_login_controller(self):
        """
        Override this method to override the login_url attribute.
        """
        login_controller = self.login_controller or settings.LOGIN_CONTROLLER
        if not login_controller:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} is missing the login_controller attribute. Define "
                f"{self.__class__.__name__}.login_controller, settings.LOGIN_CONTROLLER, or override "
                f"{self.__class__.__name__}.get_login_controller()."
            )
        return str(login_controller)

    def handle_no_permission(self):
        if self.raise_exception or self.request.user.is_authenticated:
            raise PermissionDenied(self.get_permission_denied_message())

        controller = self.get_login_controller()

        return send_redirect(url='.~{}'.format(controller), link_data={'next': '..'})


class SDCView(View):
    http_method_names = View.http_method_names + ['get_api', 'post_api', 'get_content', 'search']

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == 'post' and request.POST.get('_method') == 'search':
            request.method = 'search'

        if request.method.lower() == 'get' and request.GET.get('_method') == 'content':
            request.method = 'get_content'

        if request.method.lower() == 'post' and request.POST.get('_method') == 'api':
            request.method += '_api'

        if request.method.lower() == 'get' and request.GET.get('_method') == 'api':
            request.method += '_api'

        return super(SDCView, self).dispatch(request, *args, **kwargs)


def channel_login(function):
    @wraps(function)
    def wrap(channel, **kwargs):
        profile = channel.scope['user']
        if profile.is_authenticated:
            return function(channel, **kwargs)
        else:
            raise PermissionDenied

    return wrap
