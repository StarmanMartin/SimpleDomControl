import json
from django.urls import reverse

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.serializers.json import DjangoJSONEncoder


NEXT = 'next_controller'



def sdc_link_factory(controler: str = None, link_data: dict = None):
    idx_url = reverse('sdc_index')
    url = '{0}~{1}'.format(idx_url, controler)
    if link_data is not None:
        link_data_test = ''
        for elem in link_data:
            link_data_test += '&{0}={1}'.format(elem, link_data[elem])
        url = '{0}~{1}'.format(url, link_data_test)
    return url


def sdc_link_obj_factory(url):
    return '<a href="%s">Redirector</a>' % (url)


def send_redirect(controler: str = None, link_data: dict = None, url: str = None, **kwargs):
    kwargs['status'] = 'redirect'
    if url is not None:
        kwargs['url-link'] = sdc_link_obj_factory(url)
        kwargs['url'] = url
    elif controler is not None:
        url = sdc_link_factory(controler, link_data)
        kwargs['url-link'] = sdc_link_obj_factory(url)
        kwargs['url'] = url
    return HttpResponse(json.dumps(kwargs, cls=DjangoJSONEncoder), content_type="application/json")



def send_redirect_next(request, **kwargs):
    return send_redirect(request.session.get(NEXT, 'home-main'), **kwargs)


def send_success(template_name: str = None, context: dict = None, request = None, status= 'success', **kwargs):
    kwargs['status'] = status
    if template_name is not None:
        kwargs['html'] = render_to_string(template_name, request=request, context=context)
    return HttpResponse(json.dumps(kwargs, cls=DjangoJSONEncoder), content_type="application/json")


def send_error(template_name: str = None, context: dict = None, request=None, status=400, **kwargs):
    kwargs['status'] = 'error'
    if template_name is not None:
        kwargs['html'] = render_to_string(template_name, request=request, context=context)
    return HttpResponse(json.dumps(kwargs, cls=DjangoJSONEncoder), status=status, content_type="application/json")

def send_controller(controller_name: str):
    return HttpResponse('<%s></%s>' % (controller_name,controller_name), content_type="text/html")