Core of SDC
===========

The *SDC* package, which consists of three Django apps:
*sdc_core*, *sdc_tools*, and *sdc_user*. The *sdc_core* Django app serves as the foundation of
*SDC*. It encompasses essential components such as management command scripts and a *consumer.py*,
which acts as a handler for all *SDC* websocket requests. Additionally, the *sdc_core* app houses a
Python package named *sdc_extentions* (this spelling is the real package name,
e.g. ``from sdc_core.sdc_extentions.views import SDCView``).


Management command
------------------

The commands provided by *SDC* simplify development. They create controllers and models and update the URLs.
Let us first list all important commands:

.. code-block:: sh

    # Initialize a new SDC project
    $ python manage.py sdc_init
    # Create a new controller
    $ python manage.py sdc_cc
    # Create a new SDC model
    $ python manage.py sdc_new_model

All commands have to be run in the directory that contains *manage.py*. The
commands use the current working directory as project root. The project
package (called *main app* below) is the first part of ``ROOT_URLCONF``.

Where a command asks you to select something, it shows an interactive
selection list if the terminal is interactive. Otherwise it prints a numbered
list and reads the number(s) from the input (a comma-separated list for
multiple choices).

A brief summary of the terminal commands:

.. _sdc-init-core:

1 - sdc_init
************

The command *sdc_init* initializes SDC in your project. The *sdc_init* command has been introduced in :ref:`getting-started-label`.
*sdc_core* has to be in ``INSTALLED_APPS`` before you can run it.

.. code-block:: sh

    $ python manage.py sdc_init
    # update the SDC files of an initialized project
    $ python manage.py sdc_init -u

Options:

``-u``, ``--update``
    Update an existing SDC project. If *sdc_tools* is already in
    ``INSTALLED_APPS`` and ``-u`` is not set, the command stops with
    *"SimpleDomControl has initialized already! run sdc_init -u"*. If
    *sdc_tools* is not installed, ``-u`` is ignored.
``-y``, ``--assume-yes``
    Answer every overwrite question with *yes*.
``-n``, ``--assume-no``
    Answer every overwrite question with *no*. If both ``-y`` and ``-n`` are
    set, ``-y`` wins.

Interactive behaviour: files that do not exist yet are written without a
question. For every file that already exists the command asks
*"Would you like to overwrite <path>? (y/n) [default=n]"*. An empty answer
means *no*.

Placeholders in the template files (for example the project name) are
replaced during the copy. The indentation used in generated Python code is
taken from the *DJANGO_SETTINGS_MODULE* line of your *manage.py*.

What *sdc_init* creates or changes (paths relative to the project root):

*<main app>/settings.py* and *<main app>/base_settings.py*
    If *base_settings.py* does not exist, your *settings.py* is renamed to
    *base_settings.py*. Then a new *settings.py* is written that starts with
    ``from <main app>.base_settings import *`` and adds the SDC settings:
    ``daphne``, ``channels``, ``sdc_tools`` and ``sdc_user`` in
    ``INSTALLED_APPS``, ``ASGI_APPLICATION``, channel layers (in-memory if
    ``DEBUG``, Redis otherwise), a *jest* SQLite database selectable with the
    environment variable *DJANGO_DATABASE*, template settings,
    ``SERVER_CALL_VIA_WEB_SOCKET = False``, ``LOGIN_CONTROLLER = 'sdc-login'``,
    ``LOGIN_SUCCESS``, ``JWT``, ``AUTH_USER_MODEL = "sdc_user.SdcUser"`` and the
    ``SDC_USER_*`` settings. With ``-u`` the existing *settings.py* is only
    replaced if you answer *yes*.
*<main app>/asgi.py*
    Always deleted and written again (no question). It routes websockets to
    *routing.py* through ``AuthMiddlewareStack``.
*<main app>/routing.py*
    The websocket URL patterns: ``sdc_ws/ws/`` (``SDCConsumer``) and
    ``sdc_ws/model/<model_name>`` / ``sdc_ws/model/<model_name>/<model_id>``
    (``SDCModelConsumer``).
*ROOT_URLCONF file (e.g. <main app>/urls.py)*
    Only without ``-u``. Extends the ``from django.urls import path`` import,
    adds the URL includes for *sdc_tools* and *sdc_user*, the REST API routes
    ``sdc_api/<model>/<id>/``, ``sdc_api/<model>/`` and ``sdc_api/login/``
    (see :doc:`rest_api`) and the marker comment ``# scd view below``, which
    *sdc_cc* uses later. At the end of the file it appends an ``index`` view
    (renders *index.html*), the ``jsi18n/`` catalog, the root path ``''``
    (name ``sdc_index``) and a catch-all ``~.*`` path for client-side
    navigation.
*package.json*
    The npm package of the project (in the project root, not in *Assets*).
    It contains the gulp scripts ``build``, ``develop`` and ``sdc_test`` and
    the Jest configuration.
*.devcontainer/*
    Dockerfile, *devcontainer.json* and start scripts for a dev container.
*Assets/*
    The client build: *gulpfile.jsx*, *babel.config.json*, the webpack
    configs, *src/index.organizer.js*, *src/index.style.scss*,
    *tests/config/* (Jest setup) and *static/*.
*templates/*
    *index.html*, *base.html* and *elements/form.html*,
    *elements/inline_form.html*.
Links
    *Assets/libs/sdc_tools* and *Assets/libs/sdc_user* are created as
    symbolic links to the client files of the installed packages (see
    `5 - sdc_update_links`_).

With ``-u`` the command also adds every app that has a *sdc_views.py* to
*Assets/src/index.organizer.js* and *Assets/src/index.style.scss* again.

.. note::

    When Django starts with ``DEBUG = True`` and an *Assets* directory
    exists, *sdc_core* writes *Assets/.sdc_python_env* (the path of the
    Python interpreter, used by the gulp build) and *Assets/.sdc_env* (Jest
    database settings ``JSON_DATA_DUMP``, ``COPY_DEFAULT_DB`` and
    ``DB_PYTHON_SCRIPT``; existing values are kept).

.. _sdc-cc-core:

2 - sdc_cc
**********

The command *sdc_cc* creates a new SDC controller. A short introduction can be found here: :ref:`sdc-controller-label`.
Make sure that you are in the same directory as the *manage.py* and run:

.. code-block:: sh

    $ python manage.py sdc_cc

The command asks three questions in the terminal. Firstly, it needs to know in
which Django app the controller has to be created (we choose *mypage* in the
example below; the project package is also listed). Secondly, you have to give
the new controller a name (in the example the name is *about_me*). Important:
only use snake_case for the controller name. Thirdly, you can select
controllers to add as mixins. In a terminal, the app and mixin questions are
interactive selection lists. See :ref:`sdc-controller-label` for more details.

The questions can be answered with options instead:

.. code-block:: sh

    $ python manage.py sdc_cc -a mypage -c about_me -m
    $ python manage.py sdc_cc -a mypage -c about_me -m sdc_auto_submit,sdc_update_on_change

``-a``, ``--app_name``
    The Django app. The list contains the main app and every app in
    ``INSTALLED_APPS`` that has a directory in the project root. If the
    value is missing or not in this list, the app is asked for.
``-c``, ``--controller_name``
    The controller name in snake_case. Only lowercase letters, digits and
    ``_`` are allowed and it must start with a letter; otherwise the command
    stops with an error.
``-m``, ``--mixin_apps``
    A comma-separated list of mixin controllers in snake_case. Names that are
    not known controllers are dropped without a message. A bare ``-m`` adds
    no mixins and skips the question. Without ``-m`` you choose the mixins
    from a list of all controllers.

The command checks the settings first. It stops if
``TEMPLATES[0]['APP_DIRS']`` is not ``True`` or if ``BASE_DIR / 'templates'``
is not in ``TEMPLATES[0]['DIRS']``.

Files created or changed (``<app>`` is the app, ``<name>`` the controller
name):

- For the first controller of an app: *<app>/sdc_urls.py*,
  *<app>/sdc_views.py* and the Jest file *<app>/Assets/tests/<app>.test.js*
  are created, and ``path('sdc_view/<app>/', include('<app>.sdc_urls'))`` is
  added below ``# scd view below`` in the ROOT_URLCONF file. If the marker is
  missing, the command prints the line you have to add.
- *<app>/sdc_urls.py*: ``path('<name>', sdc_views.<Name>.as_view(),
  name='scd_view_<app>_<name>')``.
- *<app>/sdc_views.py*: a new ``SDCView`` class with ``template_name`` and a
  ``get_content`` method.
- *<app>/Assets/src/<app>/controller/<name>/<name>.js* and *<name>.scss*.
  The ``contentUrl`` of the controller is set to the new URL.
- *<app>/templates/<app>/sdc/<name>.html*.
- *<app>/Assets/src/<app>/<app>.organizer.js* and *<app>.style.scss* get an
  import of the new controller. For the first controller of an app, the app
  organizer is also added to *Assets/src/index.organizer.js* and
  *Assets/src/index.style.scss*.
- A Jest ``describe`` block for the controller is appended to
  *<app>/Assets/tests/<app>.test.js*. It creates the controller with
  ``test_utils.get_controller`` and checks that the tag is in the page.
  Run the tests with ``npm run sdc_test``.
- The links of the app are updated as in `5 - sdc_update_links`_
  (*Assets/src/<app>*, *Assets/bin/<app>*, *Assets/tests/<app>.test.js*,
  the template link in the controller directory and *.gitignore*).

.. note::

    The command prints the value of ``-m`` (``None``, ``True`` or the
    string) before it starts.

.. _sdc-new_model-core:

3 - sdc_new_model
*****************

The command *sdc_new_model* creates a new SDC Model. A short introduction can be found here: :ref:`sdc-model-label`.
Make sure that you are in the same directory as the *manage.py* and run:

.. code-block:: sh

    $ python manage.py sdc_new_model

The command asks two questions in the terminal. Firstly, it needs to know in
which Django app the model has to be created (we choose *mypage* in the example
below). Secondly, you have to give the new model a name (in the example the
name is *BookCover*). Important: only use CamelCase for the model name. See
:ref:`sdc-model-label` for more details.

The questions can be answered with options instead:

.. code-block:: sh

    $ python manage.py sdc_new_model -a mypage -m BookCover

``-a``, ``--app_name``
    The Django app (same list and behaviour as for *sdc_cc*).
``-m``, ``--model_name``
    The name of the model class in CamelCase.

The same settings check as for *sdc_cc* runs first. If a model with this
name already exists in the app, the command exits with code 1 without a
message. An empty name also exits with code 1.

Files created or changed:

- *<app>/models.py*: the SDC imports are added at the top if the file does
  not import ``SdcModel`` yet. A model class ``<Model>(models.Model,
  SdcModel)`` with a ``SearchForm``, a ``SdcMeta`` class and the methods
  ``render``, ``is_authorised`` and ``get_queryset`` is appended. The
  generated ``is_authorised`` returns ``False``, so all access is denied
  until you change it.
- *<app>/forms.py*: a ``<Model>Form(ModelForm)`` with ``fields = "__all__"``.
- *<app>/templates/<app>/models/<Model>/<Model>_details.html* and
  *<Model>_list.html* (existing files are not overwritten).
- Links of these templates in *<app>/Assets/src/<app>/models/<Model>/*.

The command does not create migrations. Run ``makemigrations`` and
``migrate`` afterwards.

4 - sdc_update_url
******************

The *sdc_update_url* command updates the *contentUrl* property of the SDC controllers.
This command is only needed if you change the auto-generated path in the *sdc_urls.py*
files manually. For example, let us add a numeric parameter to the URL path of the about me controller.

.. code-block:: diff

     ...
     urlpatterns = [
        # scd view below
    -   path('about_me', sdc_views.AboutMe.as_view(), name='scd_view_mypage_about_me'),
    +   path('about_me/<int:key>', sdc_views.AboutMe.as_view(), name='scd_view_mypage_about_me'),
     ]
     ...

*mysite/mypage/sdc_urls.py*


In this case the auto generated url to get the html of the controller would no longer be valid. To update the url simply run:

.. code-block:: sh

    $ python manage.py sdc_update_url

It automatically checks the content URL paths of each controller. If a path has changed, it updates the controller's *content_url*. The resulting changes in the controller are presented below:

.. code-block:: diff

    ...
    class AboutMeController extends AbstractSDC {

        constructor() {
            super();

    -       this.contentUrl = "/sdc_view/mypage/about_me"; //<about-me></about-me>
    +       this.contentUrl = "/sdc_view/mypage/about_me/%(key)s"; //<about-me data-key=""></about-me>
    ...

*mysite/mypage/Assets/src/mypage/controller/about_me/about_me.js*

The command has no options. It looks at every controller in
*Assets/src/<app>/controller/* of the apps in the project root (the main app
is skipped) and replaces the first ``this.contentUrl = ...`` line of
*<name>/<name>.js*. The URL is looked up by the URL name
``scd_view_<app>_<name>``.

5 - sdc_update_links
********************

All client files of an app live inside the app. For the build, they are also
linked into the global *Assets* directory, which contains the build scripts.
The *sdc_update_links* command (no options) creates these symbolic links again
for every app in ``INSTALLED_APPS`` that has a *sdc_views.py*:

- Apps inside the project: *Assets/src/<app>* links to
  *<app>/Assets/src/<app>*, *Assets/bin/<app>* links to
  *<app>/Assets/bin/<app>* and every *<app>/Assets/tests/\*.test.js* is
  linked into *Assets/tests/*.
- Installed packages (for example *sdc_tools* and *sdc_user*):
  *Assets/libs/<app>* links to *<package>/Assets/bin/<app>*.
- The HTML template *<app>/templates/<app>/sdc/<name>.html* of each
  controller is linked into its controller directory, and the model
  templates are linked into *<app>/Assets/src/<app>/models/<Model>/*.
- The app organizer is added to *Assets/src/index.organizer.js* and
  *Assets/src/index.style.scss* if it is missing.
- All created links, */node_modules/*, */static/* and
  */Assets/.sdc_python_env* are added to *.gitignore*.

The gulp build runs *sdc_update_links* and *sdc_make_model_js* before it
compiles. On Windows, symbolic links need the developer mode.

6 - sdc_get_model_infos
***********************

The *sdc_get_model_infos* command (no options) prints a JSON object with the
information IDEs need to find all files of the SDC models:

.. code-block:: python

    {"sdc_models": [
        {"name": "BookCover", "app": "mypage",
         "model_file": "...", "model_file_line": 12,
         "create_form": {"file": "...", "class": "BookCoverForm", "line": 5},
         "edit_form": {...},
         "html_detail_template": "...", "html_list_template": "...",
         "html_form_template": "..."}
    ]}

The template keys are only present if the template can be found.

7 - sdc_get_controller_infos
****************************

The *sdc_get_controller_infos* command (no options) prints a JSON object with
the information IDEs need to find all files of the SDC controllers. It reads
the controller directories in *Assets/libs/* and *Assets/src/* for apps in
``INSTALLED_APPS``:

.. code-block:: python

    {"sdc_controller": {
        "mypage": [
            {"tag_name": "about-me", "name": "about_me",
             "controller_asset_dir": "...", "sdc_view_file": ".../sdc_views.py",
             "sdc_view_file_number": 7, "url": "/sdc_view/mypage/about_me",
             "js": "...", "scss": "...", "html": "..."}
        ]
    }}

The keys ``js``, ``scss`` and ``html`` are only present if the file exists.
If *Assets/src* or *Assets/libs* is missing, the command fails with exit
code 3. *sdc_cc* uses this command to list the possible mixins.

8 - sdc_get_controller_url
**************************

.. code-block:: sh

    $ python manage.py sdc_get_controller_url mypage about_me
    /sdc_view/mypage/about_me/%(key)s

Prints the URL path of a controller. Both arguments are positional:
``app_name`` and ``controller_name`` (snake_case). URL parameters are shown as
``%(name)s``. The output is empty if no URL with the name
``scd_view_<app>_<name>`` (or the old name ``scd_view_<name>``) exists.

9 - sdc_is_installed
********************

.. code-block:: sh

    $ python manage.py sdc_is_installed

Prints *"SDC is installed!"* and exits with code 0 if *sdc_tools* is in
``INSTALLED_APPS``. Otherwise it prints *"Sdc is not installed: run
sdc_init"* and exits with code 3. No options.

10 - sdc_make_model_js
**********************

.. code-block:: sh

    $ python manage.py sdc_make_model_js

Generates the client model classes (no options). The directory
*Assets/src/models/* is deleted and written again: one *<Model>.js* per SDC
model (a subclass of ``SdcModel`` from *sdc_client* with a static ``fields``
description and getters/setters per field) and *src.js*, which imports all
classes and registers them with ``registerModel``. *Assets/src/index.organizer.js*
imports *./models/src.js*. The gulp build runs this command automatically.
See :ref:`sdc-model-label`.

11 - sdc_open_api
*****************

.. code-block:: sh

    $ python manage.py sdc_open_api

Writes an OpenAPI 3.0.3 description of the REST API to
*openapi.generated.yaml* in the current directory (no options). It contains
``/sdc_api/login/`` (``GET`` refreshes, ``POST`` logs in and returns JWT
tokens) and for every SDC model ``/sdc_api/<model>/`` (``GET`` list,
``POST`` create) and ``/sdc_api/<model>/{id}/`` (``GET``, ``PUT``,
``PATCH``). The model name in the path is lowercase. The schemas
``<Model>``, ``<Model>Create``, ``<Model>Edit`` and ``<Model>Patch`` are built
from the model fields and from ``SdcMeta.create_form`` / ``SdcMeta.edit_form``.
If a form has a file field, the request body uses *multipart/form-data*.
See :doc:`rest_api`.

.. note::

    The generated file has no ``DELETE`` operation, although the REST API
    view handles ``DELETE``.

12 - sdc_db_tools
*****************

Database helpers. Exactly one of ``-b``, ``-r``, ``-c`` or
``--update_to_sdc_user`` must be set; otherwise the command raises a
``ValueError``.

.. code-block:: sh

    $ python manage.py sdc_db_tools -b
    $ python manage.py sdc_db_tools -r -p ./backup/2026_01_31_12_00_00

``-p``, ``--path``
    Directory of the backup. Default: *./backup/<YYYY_MM_DD_HH_MM_SS>*.
``-b``, ``--backup``
    Writes the rows of every model as Django JSON, one file per model with
    rows: *<app_label>__<Model>.json*. The directory must be new or empty.
``-r``, ``--restore``
    Loads all *\*.json* files of the directory and saves each object. If
    saving fails with a foreign key error, all files are read again until no
    foreign key error is left. Other integrity errors are ignored.
``-c``, ``--clear``
    Makes a backup and then drops all tables.
``--update_to_sdc_user``
    Moves an existing database from Django's ``auth.User`` to
    ``sdc_user.SdcUser``: it runs ``migrate`` and a backup with a temporary
    settings file without ``AUTH_USER_MODEL``, changes the model of the saved
    users to ``sdc_user.sdcuser``, drops all tables, runs ``makemigrations``
    and ``migrate`` and restores the backup.

.. note::

    In version 0.159.0 ``--clear`` makes the backup and then fails with a
    ``TypeError`` before any table is dropped.

13 - sdc_shell_execute_script
*****************************

.. code-block:: sh

    $ python manage.py sdc_shell_execute_script -s ./scripts/prepare_db.py

``-s``, ``--script``
    Path of a Python file. The file is run with ``exec`` inside the command,
    so Django is set up and ``self`` (the command) is available.

If the file does not exist the command fails with exit code 2. An exception
in the script fails with exit code 3. The Jest setup uses this command: if
``DB_PYTHON_SCRIPT`` in *Assets/.sdc_env* is set to a path, the script runs
against the *jest* database before the tests.

14 - sdc_overwrite_lib_file
***************************

.. code-block:: sh

    $ python manage.py sdc_overwrite_lib_file

Copies controller files of an installed SDC package (for example
*sdc_tools* or *sdc_user*) into your project so that you can change them.
The command has no options and is always interactive: select an app from
*Assets/libs/*, then a controller, then one or more *.js* files. Each
selected file is copied to the same path below *Assets/overwrite_libs*
(*Assets/overwrite_libs/<app>/controller/<controller>/<file>*). The webpack
build then uses the copy instead of the library file; see
:ref:`sdc-build-label` for details and limits (styles cannot be overwritten
this way).

15 - Creating a new project (sdc/__main__.py)
*********************************************

The package does not install a console script. The source repository contains
a small *click* program in *sdc/__main__.py*, which is not part of the
installed package. It only works from a source checkout:

.. code-block:: sh

    $ python -m sdc new --name mysite

It runs *sdc/init.sh* in a temporary directory: it creates a *virtualenv*
*venv*, installs *django* and *simpledomcontrol* from PyPI, runs
``django-admin startproject``, adds ``sdc_core`` to ``INSTALLED_APPS`` and
``BASE_DIR / 'templates'`` to the template dirs (GNU ``sed``), runs
``sdc_init`` and ``npm install``. The directory is then moved to
*./<name>*. The output is shown after the script has finished. For the
normal setup see :ref:`getting-started-label`.


SDC extensions
--------------

The package *sdc_core.sdc_extentions* contains the server-side API that you use
in your *sdc_views.py* files. The model mixin (``SdcModel``, ``SdcMeta``,
search forms) is described in :ref:`sdc-model-label`. The REST API and JWT
login are described in :doc:`rest_api`.

SDCView
*******

Every controller has a view class in *<app>/sdc_views.py* that extends
``SDCView`` (a Django ``View``). The client calls the same URL for different
tasks and selects the handler with the request parameter ``_method``:

``get_content(self, request, *args, **kwargs)``
    ``GET`` with ``_method=content``. Returns the HTML of the controller. The
    client sends this request when the controller is loaded. URL parameters
    of the path are passed as keyword arguments.
``get_api(self, request, ...)``
    ``GET`` with ``_method=api``. Called by ``this.get(url, args)`` in the
    controller.
``post_api(self, request, ...)``
    ``POST`` with ``_method=api``. Called by ``this.post(url, args)`` in the
    controller and by forms with a hidden ``_method=api`` input.
``search(self, request, ...)``
    ``POST`` with ``_method=search``.
Server call
    ``POST`` with ``_method=sdc_server_call``, the method name in
    ``_sdc_func_name`` and the arguments as JSON in ``data``. This is what
    ``this.serverCall('name', args)`` sends. The view calls
    ``self.<name>(request, **data)``. If the method returns an
    ``HttpResponse``, it is sent as it is. Any other return value is sent
    with ``send_success(_return_data=value)``, and the client resolves the
    promise with that value.

A missing handler results in HTTP 405 (``http_method_not_allowed``).

.. code-block:: python

    from django.shortcuts import render
    from sdc_core.sdc_extentions.views import SDCView
    from sdc_core.sdc_extentions.response import send_success


    class AboutMe(SDCView):
        template_name = 'mypage/sdc/about_me.html'

        def get_content(self, request, *args, **kwargs):
            return render(request, self.template_name)

        def post_api(self, request):
            return send_success(msg='Saved')

        def add(self, request, a=0, b=0):
            return a + b  # client: await this.serverCall('add', {a: 1, b: 2})

*mysite/mypage/sdc_views.py*

If ``SERVER_CALL_VIA_WEB_SOCKET`` is ``True`` in the settings, the client sends
server calls over the websocket ``sdc_ws/ws/`` instead. The consumer imports
``<app>.sdc_views.<ControllerClass>``, checks the access mixin with
``async_check_requirements`` and calls ``method(consumer, **args)``. In this
mode the first argument is the websocket consumer, not a request. The method
may be ``async``; if it is a generator, the first yielded value is sent as the
result and the rest of the generator is run afterwards. Write server-call
methods with a neutral first parameter (e.g. ``channel=None``) and return
JSON-serialisable data if they have to work in both modes.

``is_valid_server_call(name)`` and ``SDC_SERVER_CALL_DENYLIST``
    Both server-call paths check the method name with
    ``is_valid_server_call``. It rejects empty names, names starting with
    ``_`` and every name in ``SDC_SERVER_CALL_DENYLIST``: ``as_view``,
    ``dispatch``, ``setup``, ``options``, ``http_method_not_allowed``,
    ``get_queryset``, ``is_authorised``, ``check_requirements``,
    ``async_check_requirements``, ``handle_no_permission``,
    ``handle_no_grop_permission`` and ``get_login_controller``. Every other
    public method of the view can be called by the client, so keep helper
    methods private (``_name``).

Access mixins
*************

Put the mixin before ``SDCView`` in the class bases.

.. code-block:: python

    from sdc_core.sdc_extentions.views import SDCView, SdcLoginRequiredMixin, SdcGroupRequiredMixin


    class MainView(SdcLoginRequiredMixin, SDCView):
        ...


    class EditorView(SdcGroupRequiredMixin, SDCView):
        group_required = ['Editor']
        staff_allowed = True

*mysite/mypage/sdc_views.py*

``SdcLoginRequiredMixin``
    Allows only authenticated users (``check_requirements(user)`` returns
    ``user.is_authenticated``). The check runs in ``dispatch``, so it covers
    all HTTP requests of the view including server calls.

    ``raise_exception``
        Default ``False``. If ``True``, a denied request raises
        ``PermissionDenied`` (HTTP 403).
    ``login_controller``
        Tag name of the login controller. Default ``None``, then
        ``settings.LOGIN_CONTROLLER`` is used (``'sdc-login'`` in the
        generated settings). ``get_login_controller()`` returns the value and
        raises ``ImproperlyConfigured`` if both are empty.
    ``handle_no_permission()``
        Called for a denied request. Without ``raise_exception`` it returns
        ``send_redirect(url='.~<login_controller>', link_data={'next': '..'})``,
        which opens the login controller as a sub view.

``SdcGroupRequiredMixin``
    Extends ``SdcLoginRequiredMixin``. A user is allowed if they are
    authenticated and one of these is true: they are in one of the groups of
    ``group_required``, they are a superuser, or ``staff_allowed`` is ``True``
    and they are staff.

    ``group_required``
        List of group names. Default ``[]`` (then only superusers, and staff
        if allowed, have access).
    ``staff_allowed``
        Default ``False``.
    ``handle_no_grop_permission()``
        Called when the user is logged in but not allowed. It behaves like
        ``handle_no_permission`` (``PermissionDenied`` or a redirect to the
        login controller).

For websocket server calls only ``async_check_requirements(user)`` is used; a
denied call returns a *403 Not allowed!* error to the client.

``channel_login``
    A decorator for functions with the signature ``function(channel,
    **kwargs)``. It raises ``PermissionDenied`` unless
    ``channel.scope['user']`` is authenticated.

    .. note::

        The wrapper accepts only one positional argument. On a normal
        instance method (``self`` plus the consumer) the call fails with a
        ``TypeError``, and on the HTTP path the request has no ``scope``.

Responses
*********

*sdc_core.sdc_extentions.response* contains helpers for JSON responses that
the client understands.

``send_success(template_name=None, context=None, request=None, status='success', **kwargs)``
    HTTP 200 with the JSON body ``{"status": status, ...kwargs}``. If
    ``template_name`` is set, the rendered template is added as ``html``.
``send_error(template_name=None, context=None, request=None, status=400, **kwargs)``
    JSON body ``{"status": "error", ...kwargs}`` (plus ``html`` if
    ``template_name`` is set). Here ``status`` is the HTTP status code.
``send_redirect(controller=None, back=False, link_data=None, url=None, **kwargs)``
    Tells the client to navigate. The response has HTTP status 301 and the
    JSON body ``{"status": "redirect", "url": ..., "url-link": ..., ...kwargs}``.
    ``url-link`` is an ``<a>`` element with the link, which the client uses
    to navigate. One of the arguments must be set, otherwise a ``TypeError``
    is raised. They are checked in this order:

    ``back=True``
        The URL is ``..`` (go back one sub view).
    ``url``
        Used without the index prefix (marked as deprecated in the
        docstring, but still used by the SDC apps).
    ``controller``
        A navigator path. If it does not contain the URL of ``sdc_index``
        (normally ``/``), it is prefixed with that URL and ``~``. The path follows the rules of the
        *sdc_navigator*:

        - ``/view-a/view-b``: *view-b* as sub view of *view-a*
        - ``*/view-b``: keeps the first view and shows *view-b* as sub view
        - ``../view-b``: replaces the current last sub view by *view-b*
        - ``./view-b``: adds *view-b* as next sub view to the current path

    ``link_data`` is a dict of arguments for the new controller. It is added
    as ``~&key=value&...`` (values are not URL-encoded). See
    :ref:`sdc-how-to-nav`.
``send_controller(controller_name)``
    Returns the HTML ``<controller_name></controller_name>`` (content type
    *text/html*).
``sdc_link_factory(controller=None, link_data=None, add_sdc_index=True)``
    Builds the navigation URL used by ``send_redirect``.
``NEXT``
    The string constant ``'next_controller'``.

.. code-block:: python

    from sdc_core.sdc_extentions.response import send_redirect, send_error

    def post_api(self, request):
        form = BookForm(request.POST)
        if not form.is_valid():
            return send_error(self.template_name, {'form': form}, request,
                              header='Upss!', msg='Please check the form')
        form.save()
        return send_redirect(controller='../book-list', link_data={'page': 1})

import_function
***************

``sdc_core.sdc_extentions.import_manager.import_function(string_path)`` imports
an attribute from a dotted path, e.g. ``import_function('mypage.forms.BookForm')``
returns the class. It returns ``None`` for ``None``. SDC uses it to load the
view class of a websocket server call and in *sdc_get_model_infos*.

Template tags
*************

Load the tags with ``{% load sdc_filter %}``. The libraries ``addclass``
(``addclass``, ``addformclass``, ``random_tag``) and ``indexfilter``
(``indexfilter``, ``in_list``, ``to_class_name``) contain subsets of the same
tags.

``field|addclass:"css classes"``
    Renders a form field with the given ``class`` attribute.
``field|addformclass``
    Renders a form field with Bootstrap classes: ``form-control
    form-check-input timer-change`` for checkboxes, ``form-control
    form-select timer-change`` for selects and ``form-control timer-change``
    for all other widgets.
``{% random_tag n %}``
    The current timestamp followed by ``n`` random digits.
``{% get_list_id as lid %}``
    A new UUID4 string.
``value|to_class_name``
    The class name of the value.
``list|indexfilter:i``
    ``list[int(i)]``.
``value|in_list:list``
    ``value in list``.
``value|serialize``
    ``SDC_JSON_MODEL=`` followed by JSON. A model instance is serialised with
    the ``SDCSerializer``; any other value as ``[{"fields": value}]``. Use it
    in a data attribute (``data-book="{{ book|serialize }}"``): the client
    turns such a value into an object with the fields and ``id``.

Widgets
*******

``sdc_tools.widgets.SearchableSelect(attrs=None, choices=(), multiple=False, template_name=None)``
    A select widget with a search field, rendered as the
    ``<sdc-search-select>`` controller.

    - ``choices`` is a model class, a ``QuerySet`` or a list of values. For a
      model or a queryset (and no ``template_name``), the client loads the
      options with the model view ``html_select_template`` from the
      ``SdcMeta`` of the model; a queryset limits the options to its ids.
    - ``template_name``: a template that renders the options. It gets the
      choices as ``choices``.
    - Without a model and without a template, each value is shown as an
      option.
    - ``multiple=True`` allows several values. The submitted value can be a
      list, a JSON list or a string like ``[a,b]``.

    Each option in a template must be an element with the class
    ``option-container``, ``data-value`` (the value) and ``data-search``
    (comma-separated search terms):

    .. code-block:: html

        <div data-value="{{ instance.pk }}" data-search="{{ instance.name }},{{ instance.city }}" class="option-container">
            {{ instance.name }}
        </div>

``sdc_user.widgets.ReadOnlyPassword``
    Shows a *Reset Password* link instead of the password hash. The link
    opens ``sdc-model-form`` with the ``password_form`` of ``SdcUser``. Set
    ``widget.user`` to the user; ``SdcUserChangeForm`` does this in its
    ``__init__``.

Live model updates (signals)
****************************

*sdc_core/signals.py* connects receivers to ``post_save`` and
``post_delete`` of all models. For SDC models (models with
``__is_sdc_model__``) it serialises the instance and sends it with
``group_send`` to the channel group named after the model class:

- ``post_save`` with ``created=True``: event ``on_create``.
- ``post_save`` of an existing object: event ``on_update``.
- ``post_delete``: event ``on_delete``.

Every client that has connected to the model through ``sdc_ws/model/<Model>``
is in that group. The ``SDCModelConsumer`` forwards ``on_update`` and
``on_delete`` only if the primary key is in the objects it loaded last, and
``on_create`` only if the
new object is in its queryset (``get_queryset`` plus the client filter).

Only ``Model.save()`` and ``Model.delete()`` (including cascades) send these
signals. ``QuerySet.update()``, ``bulk_create()``, ``bulk_update()`` and raw
SQL do not, so connected clients are not notified.

Messages (sdc_strings.json)
***************************

After a model form is saved or created over the websocket, the consumer adds a
``header`` and a ``msg`` to the answer. The texts come from ``MsgManager`` in
*sdc_core/consumers.py*. They are read from *<BASE_DIR>/templates/sdc_strings.json*.
If the file does not exist, default texts are built for every SDC model, and
the file is written if ``DEBUG`` is ``True``. A model that is missing in the
file is added the same way.

.. code-block:: python

    {"BookCover": {
        "save": {"header": "BookCover saved", "msg": "{0} was successfully saved"},
        "on_change": {"header": "BookCover was changed", "msg": "{0} was changed"},
        "create": {"header": "BookCover created", "msg": "{0} was successfully created"},
        "delete": {"header": "BookCover was deleted", "msg": "{0} was changed"}}}

*templates/sdc_strings.json*

Edit the file to change the texts. Each text is translated with ``gettext`` and
``{0}`` is replaced by ``str(instance)``. Only ``save`` and ``create`` are used
by the consumer.
