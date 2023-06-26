"""test_django_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.shortcuts import render
from django.conf import settings
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    re_path('sdc_view/sdc_tools/', include('sdc_tools.sdc_urls')),
    # re_path('sdc_view/sdc_user/', include('sdc_user.sdc_urls')),
    # scd view below

    path("admin/", admin.site.urls),
]
def index(request):
    return render(request, 'test_django_project/index.html', {'VERSION': settings.VERSION})

urlpatterns += [
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('', index, name='sdc_index'),
    re_path('.*', index, name='sdc_index_2'),
]
