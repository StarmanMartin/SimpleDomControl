.. _sdc-intellij-label:

IntelliJ / PyCharm plugin
=========================

The *SimpleDomControl* plugin adds an **SDC** tool window to the left side of
PyCharm. It lists all SDC controllers and SDC models of the open Django
project, opens their files with a double click, and registers the controller
tags and ``sdc_<event>`` attributes with the HTML inspections, so the IDE does
not report them as unknown.

Source code and releases: https://github.com/StarmanMartin/SimpleDomControlIntelij

Requirements
------------

- PyCharm 2026.2 or newer (build 262+). The plugin is compiled for the JBR 25
  of PyCharm 2026.2, so older IDE versions cannot load it.
- An SDC project that has been set up with ``python manage.py sdc_init`` (see
  :ref:`sdc-init-core`). The plugin needs *Assets/src* and *Assets/libs*.
- A Python interpreter with Django installed that can run the project's
  *manage.py*.

Installation
------------

1. Download ``SimpleDomControlIntelij-<version>.zip`` from the
   `releases page <https://github.com/StarmanMartin/SimpleDomControlIntelij/releases>`_.
   Do not unpack it.
2. In PyCharm open **Settings → Plugins → ⚙ → Install Plugin from Disk…** and
   select the zip.
3. Restart the IDE. The **SDC** tool window is in the left tool window bar.

Configuration
-------------

**Settings → Tools → SimpleDomControl**:

- **Python interpreter**: the executable that runs the management commands.
  The default is ``python3``. It must have Django and the project's
  dependencies installed, e.g. the project's virtualenv
  (``.venv/bin/python``).
- **manage.py directory**: the directory that contains *manage.py*. A
  relative path is resolved against the project root. Leave it empty if
  *manage.py* is in the project root.

These settings are stored per project in the workspace file
(*.idea/workspace.xml*).

The tool window
---------------

The tool window has two tabs, **Controllers** and **Models**. Each tab has a
refresh button, a search field, a tree and a status line.

Controllers
^^^^^^^^^^^

The controllers are grouped by Django app. Each controller shows its tag name
next to its name and contains:

- ``tag``: the HTML tag, e.g. ``<about-me>``
- ``url``: the content URL of the ``SDCView``, e.g. ``/sdc_view/mypage/about_me``
- ``SDCView``: the Python view class (opens at the class line)
- ``JS``, ``SCSS``, ``HTML``: the client files of the controller (only
  listed if they exist)

Models
^^^^^^

The models are grouped by Django app. Each model contains:

- ``Model``: the Python model class (opens at the class line)
- ``Create form`` / ``Edit form``: the form classes (opens at the class line)
- ``Detail template``, ``List template``, ``Form template``: the HTML
  templates (only listed if the model declares them and the template can be
  found)

Opening files
^^^^^^^^^^^^^

Double-click a file entry to open it in the editor. Python classes open at
the line of the class definition.

Search
^^^^^^

The search field filters the tree while you type. The search ignores case
and matches anywhere in the name:

- **Controllers** tab: controller name or tag name. ``about`` finds
  ``about_me`` and ``<about-me>``.
- **Models** tab: model name.

Only apps with matching entries are shown, and all results are expanded.
The matching text is highlighted, the app row shows ``matches/total``, and
the status line shows e.g. ``3 of 42 controllers match "about"``. Clear the
field to show everything again. The filter stays active after a refresh.

Refresh
^^^^^^^

The data is loaded when the tool window opens and when you press the refresh
button in either tab. A refresh always reloads both tabs. The plugin does not
watch the file system, so refresh after you create controllers or models
(``sdc_cc``, ``sdc_new_model``) or change *sdc_views.py* / *models.py*.

Errors and warnings
^^^^^^^^^^^^^^^^^^^

- If both commands fail (wrong interpreter, *manage.py* not found, project
  not initialized), both tabs show the error and a dialog shows the command
  output.
- If only one command fails, the other tab still shows its data. The failing
  tab shows the error as a ``warning:`` entry, and its status line shows the
  number of warnings in red.

HTML inspections
----------------

PyCharm reports ``<about-me>`` as an *Unknown HTML tag* and ``sdc_click`` as
an *Unknown HTML attribute* in templates. After every successful refresh the
plugin adds these names to the custom entries of the two inspections. These
are the same lists that the quick fix *Add to custom HTML tags* writes to.

- **Tags**: the ``tag_name`` of every controller.
- **Attributes**: ``sdc_`` plus every standard DOM event, e.g.
  ``sdc_click``, ``sdc_change``, ``sdc_submit``, ``sdc_input``,
  ``sdc_keyup``. These are the attributes that the client event handling
  reads (see :ref:`sdc-client-dom-events`). PyCharm's custom attributes
  cannot contain wildcards, so the plugin adds every event name
  separately. Custom event names are not registered automatically. Add
  them with the quick fix in the editor.

The plugin remembers which entries it added:

- When a controller is deleted, its tag is removed on the next refresh.
- Entries that you added yourself are never removed.
- If *sdc_get_controller_infos* fails, the registered tags are kept.

The entries are written to the inspection profile the project uses. If the
project uses the IDE-wide **Default** profile, the SDC tags are accepted in
all projects. To keep them in this project, select a **Project Default**
profile in **Settings → Editor → Inspections**. The entries are then stored
in *.idea/inspectionProfiles/* and can be committed with the project.

How it works
------------

The plugin runs two management commands of *sdc_core* in the *manage.py*
directory and reads the JSON they print:

.. code-block:: sh

   python manage.py sdc_get_controller_infos
   python manage.py sdc_get_model_infos

The output format is described in :ref:`sdc-get-infos-core`. The commands
run in the background with a timeout of 60 seconds. The plugin parses the
outermost ``{...}`` of stdout, so log output before the JSON is ignored.

Building from source
--------------------

.. code-block:: sh

   git clone https://github.com/StarmanMartin/SimpleDomControlIntelij.git
   cd SimpleDomControlIntelij
   ./gradlew buildPlugin   # zip in build/distributions/
   ./gradlew runIde        # sandbox PyCharm with the plugin installed

The build needs JDK 25. The first build downloads PyCharm Professional
(about 1 GB) for the IntelliJ Platform SDK.

Releases
^^^^^^^^

The GitHub Actions workflow *.github/workflows/build.yml* builds the zip on
every push to ``main`` and on pull requests. The zip is attached to each run
as an artifact. To publish a release:

1. Set ``version`` in *build.gradle.kts*, e.g. ``0.2.0``.
2. Commit, then push a matching tag:

   .. code-block:: sh

      git tag -a v0.2.0 -m "SimpleDomControl IntelliJ plugin 0.2.0"
      git push origin main v0.2.0

The workflow then creates a GitHub release with the zip and installation
notes.
