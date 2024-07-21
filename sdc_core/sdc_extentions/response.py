import json
from django.urls import reverse

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.serializers.json import DjangoJSONEncoder

NEXT = 'next_controller'


def sdc_link_factory(controller: str = None, link_data: dict = None, add_sdc_index: bool = True) -> str:
    """

    :param controller: path to controller
    :type controller: str, optional
    :param link_data: arguments passed to the new redirected controller
    :type link_data: dict, optional
    :param add_sdc_index:
    :return: Refactored URL
    :rtype str

    :meta private:
    """
    idx_url = reverse('sdc_index')
    if add_sdc_index and not idx_url in controller:
        url = '{0}~{1}'.format(idx_url, controller)
    else:
        url = controller
    if link_data is not None and len(link_data) > 0:
        link_data_test = ''
        for elem in link_data:
            link_data_test += '&{0}={1}'.format(elem, link_data[elem])
        url = '{0}~{1}'.format(url, link_data_test)
    return str(url)


def sdc_link_obj_factory(url: str):
    """
    :param url: a sdc url string
    :return: a html link element
    :rtype str

    :meta private:
    """
    return '<a href="%s">Redirector</a>' % (url)


def send_redirect(controller: str = None, back: bool = False, link_data: dict = None, url: str = None, **kwargs):
    """
    send_redirect is a simple way to redirect a client to another SDC controller. Set the controller argument according to
    the rules of the sdc_tools.sdc_navigator. Following you see some examples:

    - /view-a/view-b -> view-b as subview of view-a
    - */view-b -> keeps first view as it is and view-b as subview
    - ../view-b -> replaces current latest subview by view-b
    - ./view-b -> adds view-b as next latest subview to the current path

    :param controller: path to controller
    :type controller: str, optional
    :param back: if ``True`` the redirect url is equal to ``..``, default is ``False``
    :type back: boolean, optional
    :param link_data: arguments passed to the new redirected controller
    :type link_data: dict, optional
    :param url: (deprecated) Please don't use this anymore. use controller instead
    :type url: str, optional
    :param kwargs: Additional arguments send to the client
    :return: Http response with redirection command (status code 301)
    :rtype: HttpResponse
    """
    kwargs['status'] = 'redirect'
    if back:
        url = '..'
        kwargs['url'] = url
    elif url is not None:
        url = sdc_link_factory(url, link_data, add_sdc_index=False)
        kwargs['url'] = url
    elif controller is not None:
        url = sdc_link_factory(controller, link_data)
        kwargs['url'] = url
    else:
        raise TypeError("Either URL, BACK or CONTROLLER must be set")
    kwargs['url-link'] = sdc_link_obj_factory(kwargs['url'])
    return HttpResponse(json.dumps(kwargs, cls=DjangoJSONEncoder), status=301, content_type="application/json")


def send_success(template_name: str = None, context: dict = None, request=None, status='success', **kwargs):
    """

    :param template_name: HTML template name
    :type template_name: str
    :param context: Context for the html tempalte
    :type context: dict
    :param request:
    :param status:
    :param kwargs:
    :return:
    """
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
    return HttpResponse('<%s></%s>' % (controller_name, controller_name), content_type="text/html")
