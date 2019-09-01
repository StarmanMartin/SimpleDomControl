from django.urls import path, include
from django.shortcuts import render


def index(request):
    return render(request, '§MAIN_APP§/index.html', {})

urlpatterns = [
    path('', index, name='sdc_index')
]
