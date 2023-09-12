# 1 - Start new Django project



Before starting, you need to create a new Django project.  If this is your first time using Django, you’ll have to take care of some initial setup. Namely, you’ll need to auto-generate some code that establishes a Django project – a collection of settings for an instance of Django, including database configuration, Django-specific options and application-specific settings.

From the command line, **cd** into a directory where you’d like to store your code, then run the following command:(see <a href="https://docs.djangoproject.com/en/4.0/intro/tutorial01/">Djaongo Tutorial</a>)

```cmd
$ django-admin startproject mysite
```

This will create a **mysite** directory in your current directory. In the following we will continue with the **mysite** example. In your case, you will understandably have to adjust the project name.

```folder
mysite/
    manage.py
    mysite/
        __init__.py
        settings.py
        urls.py
        asgi.py
        wsgi.py
```

# 2 - Setup SDC in project

You need to change two of the generated files to setup SDC.

First you have to add in *mysite/manage.py* the path to the SDC source folder. Add the line  sys.path.insert(0, os.environ['SDC']) to the main function:

```python
...
def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    sys.path.insert(0, os.environ['SDC'])
    try:
...
```
<div class="code-block-header">mysite/manage.py</div>

Next, we need to add the following condition under **INSTALLED_APPS** in *mysite/mysite/manage.py*:  *if DEBUG: INSTALLED_APPS += ['sdc_manager']*. Additionally, we also need to make sure that the **'templates'** folder is listed in **TEMPLATES.DIRS**.

```python
...
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

if DEBUG:
    INSTALLED_APPS += ['sdc_manager']
...
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
          ...
        },
    },
]
...
```
<div class="code-block-header">mysite/mysite/settings.py</div>

Finally, from the command line, **cd** into the project directory *mysite* and run the following command:

```cmd
$ python ./manage.py sdc_init
```

This should add three new Django modules, a *templates* folder, a *sdc_example* folder and three files:

```folder
mysite/
    manage.py
    mysite/...
    sdc_core/...
    sdc_examples/...
    sdc_tools/...
    sdc_user/...
    templates/...
    .bowerrc
    .jshintrc
    bower.json
```
The following files are also altered in this process:

```git
import os

+ from channels.auth import AuthMiddlewareStack
+ from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

+ import sdc_core.routing as routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

- application = get_asgi_application()

+ application = ProtocolTypeRouter({
+     "http": get_asgi_application(),
+     "websocket": AuthMiddlewareStack(
+         URLRouter(
+             routing.websocket_urlpatterns
+         )
+     ),
+ })
```
<div class="code-block-header">mysite/mysite/asgi.py</div><br>

```git
+ VERSION=0.0

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
+    'sdc_core',
+    'channels',
+     'sdc_tools',
+     #'sdc_user'
]

+ INTERNAL_IPS = (
+     '127.0.0.1',
+ )


+ # AUTH_USER_MODEL = 'sdc_user.CustomUser'

STATIC_URL = '/static/'

+ STATIC_ROOT = './static/'

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

+ #EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
+ #EMAIL_HOST =''
+ #EMAIL_PORT = 587
+ #EMAIL_HOST_USER = ''
+ #DEFAULT_FROM_EMAIL = ''
+ #EMAIL_HOST_PASSWORD = ''
+ #EMAIL_USE_TLS = True
```
<div class="code-block-header">mysite/mysite/settings.py</div><br>

```git
+ from django.contrib import admin
- from django.urls import path
+ from django.urls import path, include
+ from django.conf.urls import url

urlpatterns = [
+   path('sdc_view/sdc_tools/', include('sdc_tools.sdc_urls')),
+   # path('sdc_view/sdc_user/', include('sdc_user.sdc_urls')),
+   # scd view below

    path('admin/', admin.site.urls),
]

+ urlpatterns += [path('', include('sdc_core.urls'))]
```
<div class="code-block-header">mysite/mysite/urls.py</div>

Before you start deveoling your web app you have to **cd** to your project directory and run:

```cmd
$ bower install
```