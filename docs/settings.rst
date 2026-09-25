.. _sdc-settings-label:

Settings and deployment
=======================

``python manage.py sdc_init`` renames your original ``settings.py`` to
``base_settings.py`` and writes a new ``settings.py`` that starts with
``from <project>.base_settings import *`` and then adds the SDC configuration.
Keep your own settings in ``base_settings.py``. Some SDC settings are only set
when ``base_settings.py`` does not define them; the others are always set by
``settings.py``. To change one of those, edit the value in ``settings.py``.

Settings written by ``sdc_init``
--------------------------------

The table lists every setting in the generated ``settings.py``. *Only if
missing* means the value is set only when ``base_settings.py`` has not defined
the setting.

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Setting
     - Value
     - Meaning
   * - ``ALLOWED_HOSTS``
     - ``['*']`` in ``DEBUG``; otherwise built from the ``ALLOWED_HOST``
       environment variable
     - See `The ALLOWED_HOST environment variable`_.
   * - ``CSRF_TRUSTED_ORIGINS``
     - Only set when ``DEBUG`` is ``False``, from ``ALLOWED_HOST``
     - The full URLs from ``ALLOWED_HOST`` (scheme, host and port).
   * - ``VERSION``
     - ``0.0`` (only if missing)
     - Passed to ``index.html`` and exposed to the client as
       ``window.VERSION``.
   * - ``INSTALLED_APPS``
     - ``['daphne'] + INSTALLED_APPS + ['channels', 'sdc_tools', 'sdc_user']``
     - ``daphne`` must come first so ``runserver`` serves ASGI. ``sdc_tools``
       and ``sdc_user`` hold the built-in controllers and the user model.
   * - ``INTERNAL_IPS``
     - ``('127.0.0.1',)`` (only if missing)
     - Standard Django setting.
   * - ``STATIC_ROOT``
     - ``BASE_DIR / 'www/'``
     - Target of ``collectstatic``.
   * - ``STATICFILES_DIRS``
     - ``[BASE_DIR / "static", BASE_DIR / "node_modules"]``
     - ``static/`` is where the client build writes its output (see
       :ref:`sdc-build-label`). ``node_modules`` makes npm packages available
       as static files.
   * - ``ASGI_APPLICATION``
     - ``'<project>.asgi.application'``
     - Entry point for daphne and channels.
   * - ``DATABASES_AVAILABLE``
     - ``{'jest': <sqlite BASE_DIR / 'test_db.sqlite3'>} | DATABASES``
     - All databases that can be selected with ``DJANGO_DATABASE``. The
       ``jest`` database is used by the JavaScript tests
       (:ref:`sdc-testing-label`). A ``jest`` entry in your own ``DATABASES``
       replaces the default one.
   * - ``DATABASES``
     - ``{'default': DATABASES_AVAILABLE[DJANGO_DATABASE]}``
     - See `The DJANGO_DATABASE environment variable`_.
   * - ``TEMPLATES``
     - ``APP_DIRS = True`` and ``BASE_DIR / "templates"`` added to ``DIRS``
     - SDC loads controller templates from app directories and the project
       templates (``base.html``, ``index.html``, ``elements/``) from
       ``templates/``.
   * - ``CHANNEL_LAYERS``
     - In ``DEBUG``: ``channels.layers.InMemoryChannelLayer``. Otherwise:
       ``channels_redis.core.RedisChannelLayer`` with
       ``hosts=[{"host": "redis", "port": 6379, "socket_timeout": 20}]``,
       ``capacity=1500``, ``expiry=10``
     - Used by the websocket consumers. In production a Redis server must be
       reachable under the host name ``redis``. ``socket_timeout`` is kept
       above the 5 second ``brpop`` timeout of ``channels_redis``; with a lower
       value, idle websockets raise "Timeout reading from redis".
   * - ``MEDIA_URL``
     - ``'/media/'`` (only if missing)
     - Also sent to the client together with loaded model data
       (``media_url``).
   * - ``MEDIA_ROOT``
     - ``BASE_DIR / 'media'`` (only if missing)
     - Standard Django setting.
   * - ``SERVER_CALL_VIA_WEB_SOCKET``
     - ``False``
     - Passed to ``index.html`` as ``window.SERVER_CALL_VIA_WEB_SOCKET``. If
       ``True``, the client sends ``serverCall`` requests over the websocket
       ``sdc_ws/ws/``; otherwise it sends them as HTTP ``POST`` requests to the
       controller URL.
   * - ``MODEL_FORM_TEMPLATE``
     - ``"elements/form.html"``
     - Default ``html_form_template`` of every ``SdcModel`` (see
       :doc:`sdc_model`).
   * - ``LOGIN_CONTROLLER``
     - ``'sdc-login'``
     - Tag name of the login controller. ``SdcLoginRequiredMixin`` (and
       ``SdcGroupRequiredMixin``) redirect there when a
       permission check fails, and ``sdc_user`` redirects to
       ``/~<LOGIN_CONTROLLER>`` after logout.
   * - ``LOGIN_SUCCESS``
     - ``'/'``
     - Default ``next_page`` of the ``sdc_user`` login controller.
   * - ``JWT``
     - ``{'secret': SECRET_KEY, 'algorithm': 'HS256', 'exp_delta_seconds': 3600}``
     - Signs the tokens of the REST API (``sdc_api/login``) and the
       e-mail confirmation and password reset tokens of ``sdc_user``. Access
       tokens expire after ``exp_delta_seconds``, refresh tokens after 20
       times that value.
   * - ``AUTH_USER_MODEL``
     - ``"sdc_user.SdcUser"``
     - The SDC user model.
   * - ``SDC_USER_GET_QUERYSET``
     - ``"sdc_user.models.sdc_user_get_queryset"``
     - Dotted path to the queryset function of ``SdcUser``. The default
       returns all users for superusers and only the user itself otherwise.
   * - ``SDC_USER_IS_AUTHORISED``
     - ``"sdc_user.models.sdc_user_is_authorised"``
     - Dotted path to the permission function of ``SdcUser``. The default
       allows self-registration for everyone, reading and editing the rows
       from ``SDC_USER_GET_QUERYSET`` for logged-in users, and deleting for
       superusers only.
   * - ``SDC_USER_FIELDS``
     - ``"__all__"``
     - ``SdcMeta.fields`` of ``SdcUser``.
   * - ``SDC_USER_FIELDS_EXCLUDE``
     - ``None``
     - ``SdcMeta.exclude`` of ``SdcUser``.

See :doc:`sdc_user` for the ``SDC_USER_*`` settings and the user model.

Settings read but not written
-----------------------------

``DEBUG``
    Standard Django setting. In ``DEBUG``, ``sdc_core`` writes
    ``Assets/.sdc_env`` and ``Assets/.sdc_python_env`` on startup (see
    :ref:`sdc-testing-label`), the websocket consumers send full error
    messages and tracebacks to the client (otherwise only "Something went
    wrong"), and ``templates/sdc_strings.json`` (the model event messages) is
    written. ``index.html`` receives it as ``window.DEBUG``.

``HOME_URL``
    Used by ``sdc_user`` to build the links in confirmation and password reset
    e-mails when the request origin is not known.

``DEFAULT_FROM_EMAIL`` and the other e-mail settings
    ``sdc_user`` sends its e-mails with Django's ``EmailMessage``. The
    generated ``settings.py`` contains commented-out examples:

    .. code-block:: python

       # EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
       # EMAIL_HOST =''
       # EMAIL_PORT = 587
       # EMAIL_HOST_USER = ''
       # DEFAULT_FROM_EMAIL = ''
       # EMAIL_HOST_PASSWORD = ''
       # EMAIL_USE_TLS = True

    Mails are sent with ``fail_silently=True``, so a wrong configuration does
    not raise an error.

.. note::

   ``HOME_URL`` is not defined by the generated settings. If ``sdc_user``
   needs the fallback and the setting is missing, sending the e-mail raises an
   ``AttributeError``.

Environment variables
---------------------

The ALLOWED_HOST environment variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With ``DEBUG = False``, ``settings.py`` reads ``ALLOWED_HOST``: a
comma-separated list of full URLs, including the scheme.

.. code-block:: sh

   export ALLOWED_HOST=https://example.com,https://www.example.com

- ``ALLOWED_HOSTS`` becomes the host names (``example.com``,
  ``www.example.com``).
- ``CSRF_TRUSTED_ORIGINS`` becomes the URLs (``https://example.com``, ...).

The variable is required. If it is missing, loading the settings fails with an
``AttributeError`` (``'NoneType' object has no attribute 'split'``). A value
without a scheme (``example.com``) has no host name after parsing and does not
work. With ``DEBUG = True`` the variable is ignored and ``ALLOWED_HOSTS`` is
``['*']``.

The DJANGO_DATABASE environment variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``DJANGO_DATABASE`` selects one entry of ``DATABASES_AVAILABLE`` as the
``default`` database. It defaults to ``'default'``. The JavaScript test setup
runs the test server with ``DJANGO_DATABASE=jest``.

.. code-block:: sh

   DJANGO_DATABASE=jest python manage.py migrate

.. note::

   The final ``DATABASES`` contains only the ``default`` alias. Other aliases
   from ``base_settings.py`` are only available through
   ``DATABASES_AVAILABLE``. An unknown name in ``DJANGO_DATABASE`` raises a
   ``KeyError``.

Deployment
----------

1. Build the client for production. This writes the bundles to ``static/``
   (see :ref:`sdc-build-label`):

   .. code-block:: sh

      npm install
      npm run build

2. Set ``DEBUG = False`` and collect the static files into ``www/``
   (``STATIC_ROOT``). This includes ``static/`` and ``node_modules``:

   .. code-block:: sh

      python manage.py migrate
      python manage.py collectstatic

3. Start Redis. With ``DEBUG = False`` the channel layer connects to the host
   ``redis`` on port ``6379``. Change ``CHANNEL_LAYERS`` in ``settings.py`` if
   your Redis server runs somewhere else.

4. Run the ASGI application with daphne. This is the command from the
   docstring of the generated ``asgi.py``:

   .. code-block:: sh

      env ALLOWED_HOST=http://localhost:8000 daphne mysite.asgi:application

Daphne serves HTTP and websockets on one port. It does not serve the files in
``www/`` and ``MEDIA_ROOT``; serve those with a web server.

.. note::

   The generated ``asgi.py`` contains
   ``os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ElnAdapter.settings')``.
   The module name is not replaced with your project name. Set
   ``DJANGO_SETTINGS_MODULE`` in the environment (for example
   ``DJANGO_SETTINGS_MODULE=mysite.settings``) or change the line to
   ``'<project>.settings'``.

Websocket routes
^^^^^^^^^^^^^^^^

``sdc_init`` writes ``<project>/routing.py``. ``asgi.py`` wraps these routes in
``AuthMiddlewareStack``, so the consumers see the logged-in Django user.

``sdc_ws/ws/``
    ``SDCConsumer``. Used for ``serverCall`` when
    ``SERVER_CALL_VIA_WEB_SOCKET`` is ``True``.

``sdc_ws/model/<model_name>``
    ``SDCModelConsumer``. The client opens one connection per queryset
    (see :doc:`sdc_model`).

``sdc_ws/model/<model_name>/<model_id>``
    Also ``SDCModelConsumer``. The client uses this path when the queryset has
    a model id. The consumer only reads ``model_name`` from the URL.
