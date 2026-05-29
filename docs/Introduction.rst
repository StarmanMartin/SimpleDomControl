What is SDC
===========

Simple-Dom-Control, or ``SDC``, is a Django-based framework for building web
applications with server-rendered HTML and a structured client runtime.

The core idea is simple:

- the server remains responsible for rendering templates, enforcing
  permissions, and handling business logic
- the browser uses controller classes to manage lifecycle, events, DOM refresh,
  and live model interaction

This gives SDC a position between classic Django pages and full SPA
architectures.

What SDC provides
-----------------

SDC combines several capabilities into one workflow:

- server-rendered controller views through Django
- generated controller and model scaffolding via management commands
- a client runtime that turns custom tags into stateful controller instances
- model synchronization between browser and Django models over WebSockets
- built-in patterns for navigation, list/detail rendering, and model forms

Architecture overview
---------------------

SDC has two main layers.

Server side
^^^^^^^^^^^

The Python package integrates with Django and provides:

- ``sdc_core`` as the foundation
- generated and manual ``SDCView`` classes
- model helpers and form/view generation for SDC models
- management commands such as ``sdc_init``, ``sdc_cc``, and ``sdc_new_model``
- routing and websocket consumers

Client side
^^^^^^^^^^^

The browser runtime, documented in this same doc set, provides:

- ``app`` for bootstrap and controller registration
- ``AbstractSDC`` as the base controller class
- ``SdcQuerySet`` and ``SdcModel`` integration for live data access
- delegated DOM events
- DOM refresh and reconciliation
- AJAX and WebSocket calls back to the server

Why SDC exists
--------------

SDC is designed for projects that want:

- Django templates and Django models to stay central
- richer client-side behavior than plain template pages provide
- a consistent controller pattern on the frontend
- server-rendered fragments instead of moving everything into a SPA
- real-time model interaction without writing a custom protocol for every page

Relationship to MVC and MVT
---------------------------

SDC intentionally mixes ideas from both MVC and MVT:

- Django still works in its normal model-view-template style on the server
- the browser adds a controller layer around the DOM
- server-rendered templates remain first-class instead of becoming an
  implementation detail

The result is best understood as a hybrid server/client controller framework
for Django rather than as a pure frontend library.
