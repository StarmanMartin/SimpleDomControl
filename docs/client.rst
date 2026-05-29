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

1. initializes DOM event delegation
2. prepares server-call connectivity
3. creates root controller objects
4. scans the DOM for all registered controller tags
5. instantiates those controllers
6. resolves ``data-*`` attributes into ``onInit()`` arguments
7. loads HTML from ``contentUrl`` if configured
8. resolves nested controllers recursively
9. wires DOM events and runs ``onRefresh()``

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

``onInit()`` arguments are populated from the controller element's
``data-*`` attributes. The parser converts common literal values into native
JavaScript types.

Example:

.. code-block:: html

   <book-list data-user-id="7" data-active="true"></book-list>

.. code-block:: javascript

   class BookList extends AbstractSDC {
     onInit(userId, active, rest) {
       this.userId = userId;   // 7
       this.active = active;   // true
       this.rest = rest;       // remaining data attributes
     }
   }

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

That is how SDC supports server-rendered HTML plus smaller client-side dynamic
regions without introducing a separate template engine.

Safe DOM operations
-------------------

SDC augments jQuery with safe DOM helpers:

- ``$elem.safeRemove()``
- ``$elem.safeEmpty()``
- ``$elem.safeReplace($new)``

These call controller removal logic before changing the DOM so child
controllers, model sockets, and event subscriptions are cleaned up correctly.

Client asset structure
----------------------

In a generated SDC project, client source files are typically organized under
``Assets``:

::

    Assets/
    ├─ src/
    │  ├─ <django_app>/
    │  ├─ sdc_tools/
    │  ├─ sdc_user/
    │  ├─ index.organizer.js
    │  └─ index.style.scss
    ├─ webpack.config/
    ├─ gulpfile.js
    └─ package.json

Older SDC projects use this directory both for the runtime package and for
application-specific controllers, styles, and linked templates.

Where to read next
------------------

- :doc:`sdc_controller` for the controller API and lifecycle
- :doc:`sdc_model` for model, queryset, and form synchronization behavior
