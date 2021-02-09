from django.urls import path, re_path
from django.shortcuts import render
from django.conf import settings

def index(request):
    return render(request, '§MAIN_APP§/index.html', {'VERSION': settings.VERSION})

urlpatterns = [
    path('', index, name='sdc_index'),
    re_path('.*', index, name='sdc_index_2')
]
