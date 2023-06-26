import json
from django.urls import reverse

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.serializers.json import DjangoJSONEncoder


NEXT = 'next_controller'



def sdc_link_factory(controler: str = None, link_data: dict = None):
    idx_url = reverse('sdc_index')
    if not idx_url in controler:
        url = '{0}~{1}'.format(idx_url, controler)
    else:
        url = controler
    if link_data is not None and len(link_data) > 0:
        link_data_test = ''
        for elem in link_data:
            link_data_test += '&{0}={1}'.format(elem, link_data[elem])
        url = '{0}~{1}'.format(url, link_data_test)
    return url


def sdc_link_obj_factory(url):
    return '<a href="%s">Redirector</a>' % (url)


def send_redirect(controller: str = None, back: bool = False, link_data: dict = None, url: str = None, **kwargs):
    kwargs['status'] = 'redirect'
    if back:
        url = '..'
        kwargs['url-link'] = sdc_link_obj_factory(url)
        kwargs['url'] = url
    elif url is not None:
        url = sdc_link_factory(url, link_data)
        kwargs['url'] = url
    elif controller is not None:
        url = sdc_link_factory(controller, link_data)
        kwargs['url-link'] = sdc_link_obj_factory(url)
        kwargs['url'] = url
    return HttpResponse(json.dumps(kwargs, cls=DjangoJSONEncoder), content_type="application/json")


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
