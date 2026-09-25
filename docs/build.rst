.. _sdc-build-label:

Building the client
===================

The client code of an SDC project is built with gulp and webpack. The build
files live in ``Assets/`` and are created by ``sdc_init``. The shared gulp
tasks come from the ``sdc_client`` package (``sdc_client/gulp/gulp.jsx``).

npm scripts
-----------

The root ``package.json`` defines three scripts:

.. code-block:: json

   "scripts": {
     "build": "gulp --gulpfile=Assets/gulpfile.jsx --mode=production",
     "develop": "gulp --gulpfile=Assets/gulpfile.jsx develop --mode=development",
     "sdc_test": "NODE_OPTIONS=--experimental-vm-modules jest"
   }

``npm run build``
    Runs the ``default`` gulp task once and writes a minified production
    build.

``npm run develop``
    Runs the ``develop`` gulp task: one development build, then it watches the
    sources and rebuilds on changes.

``npm run sdc_test``
    Runs the jest tests (see :ref:`sdc-testing-label`).

gulp runs with ``Assets/`` as its working directory, so all paths below are
relative to ``Assets/``. ``../static`` is the ``static/`` directory in the
project root, which is part of ``STATICFILES_DIRS`` (see
:ref:`sdc-settings-label`).

.. note::

   The ``--mode`` argument is not read by the gulpfile. The webpack
   configuration is chosen by ``NODE_ENV``: the ``develop`` task sets it to
   ``development``, every other task uses the production configuration.

What ``npm run build`` does
---------------------------

The ``default`` task runs these steps:

1. ``copy_statics``: copies ``Assets/static/**`` to ``static/`` (the leading
   ``static`` directory is stripped, so ``Assets/static/img/favicon.png``
   becomes ``static/img/favicon.png``).
2. ``link_files``: runs two management commands with the Python interpreter
   from ``Assets/.sdc_python_env`` (see `link_files`_):

   - ``python manage.py sdc_update_links``
   - ``python manage.py sdc_make_model_js``

3. In parallel:

   - ``scss``: compiles ``Assets/src/*.scss`` to ``static/`` (for example
     ``index.style.scss`` to ``static/index.style.css``).
   - The JavaScript series: ``clean`` (delete ``Assets/_build``),
     pre-compile (copy ``Assets/src/**/*.js`` and ``*.json`` to
     ``Assets/_build``), ``webpack`` (bundle
     ``_build/index.organizer.js`` to ``static/index.organizer.js``), then
     ``clean`` again.

The template ``templates/index.html`` loads ``index.organizer.js`` and
``index.style.css`` with ``{% static %}``.

The pre-compile step adds one line to every file that contains a class
``... extends AbstractSDC`` and an ``onInit(...)`` method. The line stores the
parameter names of ``onInit`` as ``_on_init_params`` on the class prototype.

.. note::

   The ``sdc_client`` 0.159.0 runtime does not read ``_on_init_params``. Tag
   attributes reach the controller through ``this.params``.

What ``npm run develop`` does
-----------------------------

The ``develop`` task:

1. sets ``NODE_ENV`` and ``BABEL_ENV`` to ``development``,
2. runs ``copy_statics`` and the same build as ``default`` (including
   ``link_files``), but with the development webpack configuration,
3. starts two watchers in parallel:

   ``watch_scss``
       Watches ``Assets/src/**/*.scss`` and recompiles all SCSS entry files
       when a file changes.

   ``watch_webpack``
       Watches ``Assets/src/**/*.js`` and runs the JavaScript series (clean,
       pre-compile, webpack, clean) when a file changes.

Both watchers follow symlinks, so they see the app directories linked into
``Assets/src``.

The watchers only react to changes of existing files, and they do not run
``link_files`` again. After you add a controller (``sdc_cc``), a model, or a
new app, the new links, organizer entries and generated model classes are not
picked up reliably. Restart ``npm run develop`` in that case. Changes to
controller HTML templates need no rebuild, because the templates are loaded
from the server.

link_files
----------

``link_files`` reads ``PYTHON`` from ``Assets/.sdc_python_env``. ``sdc_core``
writes this file on every Django start with ``DEBUG = True``, for example:

.. code-block:: sh

   PYTHON="/home/me/mysite/venv/bin/python"

If ``PYTHON`` is not set, gulp logs an error and continues; the links and
model classes are then not updated. In CI, write the file yourself before the
build (see :ref:`sdc-testing-label`).

``sdc_update_links`` does the following for every installed app that has a
``sdc_views.py``:

- Apps inside the project are linked to ``Assets/src/<app>`` (from
  ``<app>/Assets/src/<app>``). Their ``*.test.js`` files are linked into
  ``Assets/tests/`` and ``<app>/Assets/bin/<app>`` is linked to
  ``Assets/bin/<app>``.
- Installed packages such as ``sdc_tools`` and ``sdc_user`` are linked to
  ``Assets/libs/<app>`` (from the pre-built ``<app>/Assets/bin/<app>`` in the
  package).
- Each controller template ``<app>/templates/<app>/sdc/<controller>.html`` is
  linked next to the controller JavaScript.
- The app organizer is imported in ``Assets/src/index.organizer.js`` and its
  style in ``Assets/src/index.style.scss``, if not already present.
- Model templates are linked into ``Assets/src/<app>/models/<Model>/``.
- All created links, ``/node_modules/``, ``/static/`` and
  ``/Assets/.sdc_python_env`` are added to ``.gitignore``.

``sdc_make_model_js`` writes one class per SDC model to
``Assets/src/models/<Model>.js`` and a ``Assets/src/models/src.js`` that
imports and registers all of them (see :doc:`sdc_model`).

Import aliases
--------------

``package.json`` defines two Node subpath imports. webpack and jest both
resolve them:

.. code-block:: json

   "imports": {
     "#root/*.js": "./Assets/*.js",
     "#lib/*": "./Assets/libs/*"
   }

``#root/...``
    A ``.js`` file below ``Assets/``, for example
    ``#root/src/models/src.js``. The generated test files use it.

``#lib/...``
    A file of a linked library app, for example
    ``#lib/sdc_tools/controller/sdc_navigation_client/sdc_navigation_client.js``.
    The generated ``index.organizer.js`` imports the library organizers this
    way.

Overriding library files
------------------------

``python manage.py sdc_overwrite_lib_file`` lets you choose an app from
``Assets/libs``, one of its controllers and the ``.js`` files to copy. The
files are copied to the same path below ``Assets/overwrite_libs``, e.g.
``Assets/libs/sdc_tools/controller/sdc_dummy/sdc_dummy.js`` →
``Assets/overwrite_libs/sdc_tools/controller/sdc_dummy/sdc_dummy.js``. Edit the
copy; the library file stays unchanged.

``webpack.default.config.jsx`` contains a resolver plugin
(``OverwriteLibsPlugin``): whenever a module resolves to a file in
``Assets/libs`` and a file with the same relative path exists in
``Assets/overwrite_libs``, the build uses that file instead. This also covers
the relative imports inside the library organizers, so no import has to be
changed.

- Relative imports inside a copied file are resolved from its new location in
  ``Assets/overwrite_libs``. Copy the imported files as well, or import them
  through ``#lib/...``.
- Only the webpack build uses the overrides. The Jest tests import the
  library files directly.
- Styles cannot be overwritten this way: the library styles are included with
  relative ``@use`` paths in ``Assets/src/index.style.scss``. Add your own rules
  after those ``@use`` lines instead.
- Restart ``npm run develop`` after adding an override.

webpack configuration
---------------------

``Assets/webpack.config/`` contains four files. Each exports a function that
takes the list of entry files and returns a webpack configuration.

``webpack.default.config.jsx``
    Base configuration. One entry per file, named after the file
    (``index.organizer``), output ``[name].js``. ``.js`` files outside
    ``node_modules`` go through ``babel-loader``. Modules are resolved from
    the project ``node_modules`` first. ``symlinks: false`` resolves linked
    app directories at their link location in ``Assets/src``.

``webpack.development.config.jsx``
    Default plus ``mode: 'development'`` and source maps
    (``eval-source-map`` and ``SourceMapDevToolPlugin``).

``webpack.production.config.jsx``
    Default plus ``mode: 'production'`` and Terser minification with
    ``keep_classnames`` and ``keep_fnames``. SDC derives tag names from
    controller class names at run time, so do not remove these options.

``webpack.bundle.config.jsx``
    Production plus the externals ``jquery``, ``lodash``, ``bootstrap`` and
    ``sdc_client``, with output ``<app>/[name].js``. Used by the ``bundle``
    task.

Babel uses ``Assets/babel.config.json``. It enables ``@babel/preset-react``
with the classic runtime and ``sdcDom`` as pragma, so JSX in controller files
compiles to ``sdcDom(...)`` calls.

SCSS
----

Only the top-level files ``Assets/src/*.scss`` are compiled, by default
``index.style.scss``. It pulls in bootstrap and the app styles with ``@use``:

.. code-block:: scss

   @use "../../node_modules/bootstrap/dist/css/bootstrap";
   @use "../libs/sdc_user/sdc_user.style";
   @use "../libs/sdc_tools/sdc_tools.style";
   @use "main_app/main_app.style";

``sdc_update_links`` and ``sdc_cc`` add the ``@use`` lines for apps and
controllers.

Other gulp tasks
----------------

Run a single task with ``npx gulp --gulpfile=Assets/gulpfile.jsx <task>``.

``webpack``
    Only the webpack step. It expects ``Assets/_build`` to exist, which the
    series above creates and deletes again.

``scss``
    Only the SCSS compilation.

``link_files``
    Only ``sdc_update_links`` and ``sdc_make_model_js``.

``clean``
    Deletes ``Assets/_build``.

``copy_statics``
    Copies ``Assets/static/**`` to ``static/``.

``watch_scss`` / ``watch_webpack``
    The two watchers of ``develop``, without the initial build.

``bundle``
    Builds a reusable app package into ``Assets/bin``: ``copy_statics``,
    ``link_files``, then compiles ``Assets/src/*/*.scss`` to ``Assets/bin``
    and bundles every ``_build/<app>/*.js`` (except models) with the bundle
    configuration.

``bundle_dev``
    ``copy_statics``, then pre-compiles ``Assets/src`` and copies the
    unbundled JavaScript from ``_build`` to ``Assets/bin``. It runs neither
    ``link_files`` nor SCSS.
