.. _getting-started-label:

Version 0.57.4
================


Getting Started
===============

In the following steps, we provide a brief introduction on how to initiate a new project. Throughout this introduction, we will refer to the project as *'mysite'*.


To start a new SDC project, open your command line and cd to the directory
where you want to start your code. Then, execute the following commands:

-- code-block:: sh

    $ pip install simpledomcontrol
    $ sdc new



Quick and dirty
***************

Navigate to your project container directory and run the following chell commands:

.. code-block:: sh

    $ PROJECT_NAME = <project_name>
    $ django-admin startproject $PROJECT_NAME
    $ cd ./$PROJECT_NAME
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install simpledomcontrol
    $ sed -i "s/INSTALLED_APPS = \[/INSTALLED_APPS = ['sdc_core',/g" ./$PROJECT_NAME/settings.py
    $ sed -i "s/'DIRS'\: \[\]/'DIRS'\: \[BASE_DIR \/ 'templates'\]/g" ./$PROJECT_NAME/settings.py
    $ python manage.py sdc_init
    $ npm install


Start new Django project
************************

Before you begin, you'll need to create a new Django project.
If you're new to Django, there are some initial setup steps to follow.
Specifically, you'll need to auto-generate some code that establishes
a Django project – a set of configurations for a Django instance,
including database settings, Django-specific options,
and application-specific configurations.

To get started, open your command line and navigate to the directory
where you want to store your code. Then, execute the following command:

.. code-block:: sh

    $ cd your_chosen_directory
    $ django-admin startproject mysite

For more detailed instructions, you can refer to the `Django documentation <https://docs.djangoproject.com/en/4.0/intro/tutorial01/>`_

This command will create a new project directory.
We will continue using the mysite example in the following steps. Naturally, i
n your case, you will need to customize the project name as per your requirements.

::

    └─ your_chosen_directory/
       └─ mysite/
          ├─ manage.py
          └─ mysite/
             ├─ __init__.py
             ├─ settings.py
             ├─ urls.py
             ├─ asgi.py
             └─ wsgi.py


Setup SDC in project
********************

To integrate SDC into your project,
you'll need to make a few adjustments in the *settings.py* file.
Firstly, add *SDC* to the *INSTALLED_APPS* section.
Secondly, ensure that *BASE_DIR / 'templates'* is
included in the template settings, as illustrated below:

.. code-block:: python

    ...

    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'sdc_core',
    ]

    ...

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [BASE_DIR / 'templates'],
            'APP_DIRS': True,
            'OPTIONS': {
              ...
            },
        },
    ]

    ...

*./mysite/mysite/settings.py*

Finally, from the command line, **cd** into the project directory *mysite* and run the following command:

.. code-block:: sh

    $ cd .mysite
    $ python ./manage.py sdc_init


This should add four new Django modules to the *INSTALLED_APPS*, a *templates* folder, a *Assert* folder, a *sdc_example* folder and a few files:

::

    └─ your_chosen_directory/
       └─ mysite/
          ├─ template/
             ├─ base.html
             └─ index.html
          ├─ Assets/
             └─ ...
          ├─ manage.py
          └─ mysite/
             ├─ routing.py
             └─ ...



The following files are also altered in this process:

.. code-block:: diff

    import os
    + os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ElnAdapter.settings')

    + import django
    + django.setup()

    + from channels.auth import AuthMiddlewareStack
    + from channels.routing import ProtocolTypeRouter, URLRouter
    + from . import routing
    from django.core.asgi import get_asgi_application

    - os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

    - application = get_asgi_application()

    + application = ProtocolTypeRouter({
    +     "http": get_asgi_application(),
    +     "websocket": AuthMiddlewareStack(
    +         URLRouter(
    +             routing.websocket_urlpatterns
    +         )
    +     ),
    + })

*./mysite/mysite/asgi.py*

.. code-block:: diff

   + from django.urls import re_path

   + from sdc_core import consumers

   + websocket_urlpatterns = [
   +     re_path(r'sdc_ws/ws/$', consumers.SDCConsumer.as_asgi()),
   +     re_path(r'sdc_ws/model/(?P<model_name>\w+)$', consumers.SDCModelConsumer.as_asgi()),
   +     re_path(r'sdc_ws/model/(?P<model_name>\w+)/(?P<model_id>\d+)', consumers.SDCModelConsumer.as_asgi()),
   + ]

*./mysite/mysite/routing.py*

.. code-block:: diff

    ...
    + import os
    + from urllib.parse import urlparse, urlunparse

    ...

    - ALLOWED_HOSTS = []
    + # ALLOWED_HOSTS = []

    # Application definition

    + if not DEBUG:
    +     hosts = [urlparse(x)  for x in os.environ.get('ALLOWED_HOST').split(',')]
    +     ALLOWED_HOSTS = [host.hostname for host in hosts]
    +     CSRF_TRUSTED_ORIGINS = [urlunparse(x) for x in hosts]
    + else:
    +     ALLOWED_HOSTS = ['*']

    + VERSION=0.0

    INSTALLED_APPS = [
    +    'daphne',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    +    'channels',
    +    'sdc_tools',
    +    'sdc_user',
         'sdc_core'
    ]

    + INTERNAL_IPS = (
    +     '127.0.0.1',
    + )

    ...

    + STATIC_ROOT = 'BASE_DIR /  'www/'

    + ASGI_APPLICATION = 'mysite.asgi.application'

    + if DEBUG:
    +     CHANNEL_LAYERS = {
    +         "default": {
    +             "BACKEND": "channels.layers.InMemoryChannelLayer"
    +         }
    +     }
    + else:
    +     CHANNEL_LAYERS = {
    +         'default': {
    +             'BACKEND': 'channels_redis.core.RedisChannelLayer',
    +             'CONFIG': {
    +                 "hosts": [('redis', 6379)],
    +             },
    +         },
    +     }

    + MEDIA_URL = '/media/'
    + MEDIA_ROOT = './media/'

    + MODEL_FORM_TEMPLATE = "elements/form.html"
    + LOGIN_CONTROLLER = 'sdc-login'
    + LOGIN_SUCCESS = '/'


    + #EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    + #EMAIL_HOST =''
    + #EMAIL_PORT = 587
    + #EMAIL_HOST_USER = ''
    + #DEFAULT_FROM_EMAIL = ''
    + #EMAIL_HOST_PASSWORD = ''
    + #EMAIL_USE_TLS = True

*./mysite/mysite/settings.py*

.. code-block:: diff

   + from django.contrib import admin
   + from django.urls import path, re_path, include
   + from django.shortcuts import render
   + from django.conf import settings
   + from django.views.i18n import JavaScriptCatalog

   urlpatterns = [
   +     re_path('sdc_view/sdc_tools/', include('sdc_tools.sdc_urls')),
   +     re_path('sdc_view/sdc_user/', include('sdc_user.sdc_urls')),
   +     # scd view below

       path('admin/', admin.site.urls),
   ]

   + def index(request):
   +     return render(request, 'index.html', {'VERSION': settings.VERSION})

   + urlpatterns += [
   +     re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
   +     path('', index, name='sdc_index'),
   +     re_path('~.*', index, name='sdc_index_2'),
   + ]

*./mysite/mysite/urls.py*

The above changes include all server-side modifications.
All changes in the Asserts folder have been skipped here
for the moment. In the following the client side modifications are presented.

The *sdc_example* can be ignored.
It only contains a few examples to facilitate the development.

The SDC client
**************

The whole client is organized in the *Assets* directory

::

    └─ ...
       ├─ Assets/
          ├─ src/
             ├─ sdc_tools/
                └─ ...
             ├─ sdc_user/
                └─ ...
             ├─ simpleDomControl/
                └─ ...
             ├─ index.organizer.js
             └─ index.style.scss
          ├─ webpack.config/
             ├─ webpack.development.config.js
             ├─ webpack.production.config.js
             └─ webpack.default.config.js
          ├─ .babelrc
          └─ gulpfile.js
       ├─ package.json
       └─ ...

Let's first look at the dependencies in the package.json
file. The following list presents all the development dependencies.

.. include:: js_dev_deps.rst

All development dependencies are necessary for the build process.
The remaining dependencies need to be installed for the error-free application of SDC

.. include:: js_deps.rst

Please run the following to initialize the client.

.. code-block:: sh

    $ npm install

And you are done!!