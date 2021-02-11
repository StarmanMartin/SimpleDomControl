from django.views import View


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
