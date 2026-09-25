The Client Runtime
==================

This page documents the JavaScript runtime used by SDC projects. It replaces
the older asset-pipeline-only description with the current client architecture.

Overview
--------

The SDC client is responsible for:

- registering controller classes against custom HTML tags
- creating controller instances when those tags appear in the DOM
- loading controller HTML from Django views
- delegating DOM events to controller methods
- refreshing and reconciling DOM updates
- making server calls through AJAX or WebSockets
- synchronizing server-backed models in the browser

Primary exports
---------------

The client package exposes:

``app``
   Global runtime object.

``AbstractSDC``
   Base class for browser controllers.

``SdcModel`` and ``SdcQuerySet``
   Model APIs for live server-backed data.

``on()``, ``trigger()``, ``allOff()``, ``setEvent()``
   Application event bus helpers.

Bootstrap flow
--------------

When ``app.init_sdc()`` runs, the client:

1. on the first call, installs the safe jQuery helpers (see below)
2. prepares server-call connectivity
3. initializes DOM event delegation
4. creates the root controller objects
5. creates the controllers registered with ``app.registerGlobal()``
6. scans the page body for all registered controller tags and instantiates
   those controllers
7. reads ``data-*`` attributes into ``this.params``
8. loads HTML from ``contentUrl`` if configured and runs ``onLoad()``
9. resolves nested controllers recursively and runs ``willShow()``
10. wires DOM events and runs ``onRefresh()``

``app.init_sdc()`` returns a promise that resolves when all controllers on the
page are loaded.

Tag registration
----------------

Controllers are mapped from class names to tag names automatically.

- ``HelloWorld`` becomes ``<hello-world>``
- ``UserListController`` becomes ``<user-list>``

Example:

.. code-block:: javascript

   import { app, AbstractSDC } from "sdc_client";

   class Dashboard extends AbstractSDC {
     constructor() {
       super();
       this.contentUrl = "/sdc_view/main_app/dashboard";
     }
   }

   app.register(Dashboard);
   app.init_sdc();

DOM parameter binding
---------------------

The controller element's ``data-*`` attributes are collected into the object
``this.params``, which is available from ``onLoad()`` onward. The parser
converts common literal values into native JavaScript types. Dashed attribute
names become camelCase keys (jQuery ``.data()`` naming); underscores are kept.

Example:

.. code-block:: html

   <book-list data-user-id="7" data-active="true"></book-list>

.. code-block:: javascript

   class BookList extends AbstractSDC {
     onLoad($html) {
       this.userId = this.params.userId;   // 7
       this.active = this.params.active;   // true
       return super.onLoad($html);
     }
   }

``onInit()`` is no longer called by the runtime.

``contentUrl`` and HTML loading
-------------------------------

If a controller sets ``contentUrl``, the runtime fetches HTML for it from the
backend. Responses are cached per tag unless ``contentReload`` is true.

If the URL contains placeholders such as ``%(pk)s``, the runtime fills them
from controller tag data and enables reload behavior automatically.

Dynamic DOM fragments
---------------------

The runtime supports handler-bound placeholders such as ``<this.listview>``.
During refresh, the client calls the matching controller method and reconciles
its result back into the DOM.

- The method name is the tag name in lower case (HTML tag names are not
  case-sensitive), so ``<this.listView>`` calls ``listview()``. Use lower-case
  or snake_case method names for placeholders.
- The method receives the placeholder's ``data-*`` attributes as one object:
  ``<this.borrow_btn data-pk="7">`` calls ``borrow_btn({pk: 7})``.
- The method may return HTML, a jQuery object, or a promise of either.
- The method is looked up on the closest controller that contains the
  placeholder. A placeholder inside a model list template shown by
  ``<sdc-list-view>`` is therefore resolved on the list view, not on the page
  controller around it.

That is how SDC supports server-rendered HTML plus smaller client-side dynamic
regions without introducing a separate template engine.

Safe DOM operations
-------------------

SDC augments jQuery with safe DOM helpers:

- ``$elem.safeRemove()``
- ``$elem.safeEmpty()``
- ``$elem.safeReplace($new)``

These call ``remove()`` on the affected controllers before changing the DOM, so
child controllers, model sockets, and event subscriptions are cleaned up. The
DOM change always happens, even if a controller's ``onRemove()`` returns
``false``. ``safeEmpty()`` removes the element children only, not text nodes.

Client asset structure
----------------------

In a generated SDC project, the controller files live in each Django app and
are linked into the top-level ``Assets`` directory, which also holds the build
setup:

::

    mysite/
    ├─ package.json                  # JS dependencies and yarn/npm scripts
    ├─ Assets/
    │  ├─ src/
    │  │  ├─ <django_app>/           # links to <django_app>/Assets/src/<django_app>/
    │  │  ├─ models/                 # generated client model classes
    │  │  ├─ index.organizer.js
    │  │  └─ index.style.scss
    │  ├─ libs/
    │  │  ├─ sdc_tools/              # links to the installed sdc_tools controllers
    │  │  └─ sdc_user/
    │  ├─ tests/
    │  ├─ webpack.config/
    │  └─ gulpfile.jsx
    └─ <django_app>/
       └─ Assets/src/<django_app>/controller/<controller_name>/
          ├─ <controller_name>.js
          ├─ <controller_name>.html
          └─ <controller_name>.scss

Library controllers from ``sdc_tools`` and ``sdc_user`` can be imported through
the ``#lib/`` alias, for example
``#lib/sdc_tools/controller/sdc_navigation_client/sdc_navigation_client.js``.

Where to read next
------------------

- :doc:`sdc_controller` for the controller API and lifecycle
- :doc:`sdc_model` for model, queryset, and form synchronization behavior
