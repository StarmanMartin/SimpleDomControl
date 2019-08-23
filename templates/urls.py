from django.urls import path, include
from django.shortcuts import render


def index(request):
    return render(request, 'scd_core/index.html', {})

urlpatterns = [
    path('', index, name='sdc_index')
]
