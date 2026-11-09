import json
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.http import HttpResponse, JsonResponse  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from sdc_core.sdc_extentions.response import send_redirect  # noqa: E402
from sdc_core.sdc_extentions.views import SDCView  # noqa: E402


def _view(result):
    class View(SDCView):
        def get_content(self, request, *args, **kwargs):
            return result

    return View.as_view()


def _content(result):
    return _view(result)(RequestFactory().get('/', {'_method': 'content'}))


def test_plain_html_response_is_wrapped():
    response = _content(HttpResponse('<p>hi</p>'))
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == {'html': '<p>hi</p>', 'data': {}}


def test_html_data_tuple():
    response = _content((HttpResponse('<p>hi</p>'), {'count': 3}))
    assert json.loads(response.content) == {'html': '<p>hi</p>', 'data': {'count': 3}}


def test_string_data_tuple():
    response = _content(('<p>hi</p>', [1, 2]))
    assert json.loads(response.content) == {'html': '<p>hi</p>', 'data': [1, 2]}


def test_redirect_is_passed_through():
    redirect = send_redirect(url='..')
    assert _content(redirect) is redirect
    assert _content((redirect, {'x': 1})) is redirect


def test_error_and_json_responses_are_passed_through():
    error = HttpResponse('nope', status=403)
    assert _content(error) is error
    json_response = JsonResponse({'a': 1})
    assert _content(json_response) is json_response


def test_non_content_get_is_untouched():
    class View(SDCView):
        def get(self, request, *args, **kwargs):
            return HttpResponse('<p>raw</p>')

    response = View.as_view()(RequestFactory().get('/'))
    assert response.content == b'<p>raw</p>'
