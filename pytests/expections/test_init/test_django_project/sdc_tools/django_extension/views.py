from django.core.exceptions import PermissionDenied
from django.views import View
from functools import wraps
from django.http import HttpResponseRedirect


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
