from django.urls import path, re_path
from django.shortcuts import render
from django.conf import settings
from django.views.i18n import JavaScriptCatalog


def index(request):
    return render(request, '§MAIN_APP§/index.html', {'VERSION': settings.VERSION})

urlpatterns = [
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('', index, name='sdc_index'),
    re_path('.*', index, name='sdc_index_2'),
]
