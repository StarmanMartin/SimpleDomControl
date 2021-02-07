from django.urls import path, include
from django.shortcuts import render
from django.conf import settings

def index(request):
    return render(request, '§MAIN_APP§/index.html', {'VERSION': settings.VERSION})

urlpatterns = [
    path('', index, name='sdc_index')
]
