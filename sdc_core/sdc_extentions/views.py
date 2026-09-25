import asyncio
import json

from channels.db import database_sync_to_async
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.http import HttpResponse
from django.views import View
from functools import wraps
from sdc_core.sdc_extentions.response import send_redirect, send_success
from django.conf import settings

# Methods a client must never be able to invoke through an `sdc_server_call`
# dispatch, on top of the blanket rule that private/dunder names are rejected.
SDC_SERVER_CALL_DENYLIST = frozenset({
    'as_view', 'dispatch', 'setup', 'options', 'http_method_not_allowed',
    'get_queryset', 'is_authorised', 'check_requirements',
    'async_check_requirements', 'handle_no_permission',
    'handle_no_grop_permission', 'get_login_controller',
})


def is_valid_server_call(name) -> bool:
    """
    Guard for client-supplied server-call method names. Rejects empty names,
    private/dunder names, and known framework internals so a client cannot reach
    arbitrary view/controller methods via ``getattr``.
    """
    return bool(name) and not name.startswith('_') and name not in SDC_SERVER_CALL_DENYLIST


class SdcAccessMixin(AccessMixin):

    async def async_check_requirements(self, user):
        return self.check_requirements(user)

    def check_requirements(self, user):
        return True

    def dispatch(self, request, *args, **kwargs):
        # noinspection PyUnresolvedReferences
        return super().dispatch(request, *args, **kwargs)

class SdcLoginRequiredMixin(SdcAccessMixin):
    """Verify that the current user is authenticated."""

    async def async_check_requirements(self, user):
        return self.check_requirements(user)

    def check_requirements(self, user):
        return user.is_authenticated

    login_controller = None
    request = None

    def dispatch(self, request, *args, **kwargs):
        if not (self.check_requirements(request.user)):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

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
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())

        controller = self.get_login_controller()

        return send_redirect(url='.~{}'.format(controller), link_data={'next': '..'})


class SdcGroupRequiredMixin(SdcLoginRequiredMixin):
    group_required: list[str] = []
    staff_allowed: bool = False


    def _get_groups(self, user):
        user_groups = []
        for group in user.groups.values_list('name', flat=True):
            user_groups.append(group)
        return user_groups

    async def async_check_requirements(self, user):
        if not await super().async_check_requirements(user):
            return False
        user_groups = await database_sync_to_async(self._get_groups)(user)

        return self._check_groups(user_groups, user)

    def check_requirements(self, user):
        if not super().check_requirements(user):
            return False
        user_groups = []
        for group in  self._get_groups(user):
            user_groups.append(group)

        return self._check_groups(user_groups, user)

    def _check_groups(self, user_groups, user):
        return len(set(user_groups).intersection(self.group_required)) > 0 or user.is_superuser or (self.staff_allowed and user.is_staff)

    def dispatch(self, request, *args, **kwargs):
        if not super().check_requirements(request.user):
            return self.handle_no_permission()
        elif not self.check_requirements(request.user):
            return self.handle_no_grop_permission()
        return super().dispatch(request, *args, **kwargs)

    def handle_no_grop_permission(self):
        if self.raise_exception:
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

        if request.method.lower() == 'post' and request.POST.get('_method') == 'sdc_server_call':
            func_name = request.POST.get('_sdc_func_name')
            if not is_valid_server_call(func_name):
                return self.http_method_not_allowed(request, *args, **kwargs)
            handler = getattr(self, func_name, self.http_method_not_allowed)
            res = handler(request, **json.loads(request.POST.get('data', '{}')))
            if isinstance(res, HttpResponse):
                return res
            return send_success(_return_data=res)

        return super(SDCView, self).dispatch(request, *args, **kwargs)


def _channel_user(channel):
    # WebSocket calls pass the consumer (user in scope), HTTP calls the request.
    scope = getattr(channel, 'scope', None)
    if isinstance(scope, dict) and 'user' in scope:
        return scope['user']
    return getattr(channel, 'user', None)


def channel_login(function):
    """
    Decorator for server-call methods (and functions) that requires a logged-in
    user. Works for HTTP calls (the channel is the request) and WebSocket calls
    (the channel is the consumer), for sync and ``async`` methods. The channel is
    the last positional argument. Raises ``PermissionDenied`` otherwise.
    """
    def check(args):
        user = _channel_user(args[-1]) if args else None
        if user is None or not user.is_authenticated:
            raise PermissionDenied

    if asyncio.iscoroutinefunction(function):
        @wraps(function)
        async def async_wrap(*args, **kwargs):
            check(args)
            return await function(*args, **kwargs)

        return async_wrap

    @wraps(function)
    def wrap(*args, **kwargs):
        check(args)
        return function(*args, **kwargs)

    return wrap
