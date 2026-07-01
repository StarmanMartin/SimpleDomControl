.. _sdc-controller-label:

SDC Controllers
===============

An SDC controller is the main browser-side unit of behavior. It is a JavaScript
class that extends ``AbstractSDC`` and is bound to a custom HTML tag.

Controllers connect:

- the Django-rendered HTML fragment
- the controller lifecycle
- delegated DOM events
- refresh and reconciliation
- server calls
- model/queryset access

Creating a controller
---------------------

The recommended way to create a new controller is:

.. code-block:: sh

   python manage.py sdc_cc -a <django_app_name> -c <controller_name>

Use snake_case for the generated controller name. The command creates the
template, JavaScript, and style files and wires the corresponding Django view
entry point.

Server side of a controller
---------------------------

A typical SDC controller corresponds to a Django ``SDCView`` entry that renders
its HTML fragment through ``get_content()``.

Example:

.. code-block:: python

   class MainView(SDCView):
       template_name = "main_app/sdc/main_view.html"

       def get_content(self, request, *args, **kwargs):
           return render(request, self.template_name)

The client-side controller points its ``contentUrl`` at that endpoint.

Example:

.. code-block:: javascript

   class MainViewController extends AbstractSDC {
     constructor() {
       super();
       this.contentUrl = "/sdc_view/main_app/main_view";
     }
   }

Client files
------------

An SDC controller usually has three client-related files:

- ``<controller>.js``
- ``<controller>.scss``
- ``<controller>.html`` linked to the Django template

The JavaScript controller
-------------------------

Controllers extend ``AbstractSDC``.

Important instance properties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``contentUrl``
   Backend endpoint for the controller HTML fragment.

``contentReload``
   If true, the HTML is reloaded instead of using cached content.

``events``
   Event definition objects merged into one controller event map.

``load_async``
   If true, parent initialization does not wait for this controller.

``$container``
   jQuery wrapper for the controller DOM element.

Lifecycle
---------

The controller lifecycle has these main steps:

1. constructor
2. ``onInit(...)``
3. ``onLoad(html)``
4. nested controller/content preparation
5. ``willShow()``
6. ``onRefresh(originController)``
7. repeated refreshes as needed
8. ``onRemove()`` during cleanup

``onInit(...)``
^^^^^^^^^^^^^^^

Runs immediately after the controller is created. Parameters are taken from the
controller tag's ``data-*`` attributes.

``onLoad(html)``
^^^^^^^^^^^^^^^^

Runs after the HTML fragment has been fetched and before nested controllers are
replaced. This is the normal place to mutate or extend the loaded HTML.

``willShow()``
^^^^^^^^^^^^^^

Runs after child content has been prepared and before the refresh phase
finishes.

``onRefresh(originController)``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Runs after event wiring and DOM updates are complete.

``onRemove()``
^^^^^^^^^^^^^^

Runs when the controller is being removed. Returning ``false`` cancels removal.

Example controller
------------------

.. code-block:: javascript

   class CatalogController extends AbstractSDC {
     constructor() {
       super();
       this.contentUrl = "/sdc_view/main_app/catalog";
       this.events.unshift({
         click: {
           ".reload-button": "reloadList",
         },
       });
     }

     onInit(category = "all") {
       this.category = category;
     }

     onLoad(html) {
       $(html).find(".heading").text(`Category: ${this.category}`);
       return super.onLoad(html);
     }

     reloadList() {
       return this.reload();
     }
   }

DOM events
----------

SDC delegates browser events through the runtime rather than binding handlers
directly to each node every time content changes.

You can define events declaratively:

.. code-block:: javascript

   this.events.unshift({
     click: {
       ".save-button": "save",
       ".delete-button": "removeItem",
     },
     submit: {
       "form": "submitForm",
     },
   });

Or directly in HTML with ``sdc_<event>`` attributes:

.. code-block:: html

   <button sdc_click="save">Save</button>

Refresh and reconciliation
--------------------------

Controllers expose three important DOM update helpers:

``refresh()``
   Re-runs controller replacement and dynamic ``<this.*>`` handler blocks in the
   controller subtree.

``reload()``
   Reloads the HTML fragment from ``contentUrl`` and reconciles it into the
   existing DOM.

``reconcile($virtualNode, $realNode = null)``
   Diffs virtual and real DOM trees and preserves matching branches where
   possible.

The reconciliation step is important because it helps preserve stable DOM nodes,
especially form elements, across updates.

Mixins
------

Controllers can aggregate other controller classes as mixins through
``app.register(...).addMixin(...)``. Mixin methods and event definitions are
merged into the concrete controller instance.

Server calls
------------

Use ``serverCall(methodName, args)`` to invoke a backend method associated with
the controller.

Example:

.. code-block:: javascript

   approve() {
     return this.serverCall("approve", { approved: true });
   }

``serverCall("approve", …)`` invokes a method named exactly ``call_approve`` on
the ``SDCView`` that serves the controller (use ``call_async_<name>`` for async
work). The method name is matched verbatim.

.. warning::

   **Name guard (security).** Method names that start with ``_`` or that collide
   with framework internals (``dispatch``, ``get_queryset``, ``is_authorised``, …)
   are rejected. Name your callables plainly.

.. note::

   **Transport.** ``serverCall`` uses one transport for the whole app, chosen by a
   single flag — there is no per-call option. The default is **HTTP POST**. Set
   ``SERVER_CALL_VIA_WEB_SOCKET = True`` in ``settings.py`` (exposed to the client
   as ``window.SERVER_CALL_VIA_WEB_SOCKET``) to route calls over the WebSocket
   instead; that transport requires an ASGI server such as ``daphne``.

Forms and models
----------------

Controllers can create querysets with ``querySet(modelName, modelQuery)`` and
use the built-in model form submit pipeline.

The default model form flow:

- reads the bound ``SdcModel`` from the form metadata
- synchronizes form values back into the model
- uses ``save()`` or ``create()`` automatically
- clears or re-renders validation errors
- notifies the current controller and descendant controllers through optional
  callbacks

See :doc:`sdc_model` for the model side of that behavior.

Built-in controllers in ``sdc_tools``
-------------------------------------

The ``sdc_tools`` app ships a small set of reusable controllers. They are thin
building blocks on top of ``AbstractSDC`` and cover the most common page
patterns in an SDC application.

Overview
^^^^^^^^

``sdc-navigator``
   Main controller router. It manages the active controller path, browser
   history, breadcrumbs, menu activation, modal navigation, and nested detail
   containers.

``sdc-navigation-client``
   Base class for pages that are loaded through ``sdc-navigator``. It reports
   itself back to the navigator through the ``navLoaded`` event and exposes the
   current navigator and active controller path.

``sdc-list-view``
   Renders a model list view from a queryset and refreshes itself after model
   create, update, or delete events.

``sdc-detail-view``
   Loads a single model instance and renders its detail view. It also refreshes
   automatically when that instance updates.

``sdc-search-view``
   Wraps a search form and optional paging controls. It delegates the actual
   filtering to the parent controller through ``onSearch(form)``.

``sdc-model-form``
   Creates or edits a model through the generated SDC form pipeline. It can
   autosave, stay on the edit page, reset after save, or redirect to another
   controller.

``sdc-auto-submit``
   Adds AJAX form submission behavior to forms with the ``.ajax-form`` class.
   Success and error messages are emitted through the global alert messenger.

``sdc-alert-messenger``
   Displays short-lived global status or error messages in response to the
   ``pushMsg`` and ``pushErrorMsg`` runtime events.

``sdc-search-select``
   Searchable single- or multi-select component. It can work with static option
   markup or a model-backed option list.

``sdc-update-on-change``
   Reusable mixin that debounces change handling for elements marked with the
   ``.timer-change`` class.

``sdc-error`` and ``sdc-dummy``
   Minimal utility controllers for fallback and placeholder content.

Navigator pattern
^^^^^^^^^^^^^^^^^

``sdc-navigator`` is the runtime entry point for controller-based page
navigation. It listens to global events such as ``goTo``,
``onNavigateToController``, ``navigateToPage``, ``changeMenu``, ``navLoaded``,
``login``, and ``logout``.

Typical shell markup:

.. code-block:: html

   <sdc-navigator data-default-controller="dashboard">
     <nav>
       <a class="navigation-links" href="/dashboard">Dashboard</a>
       <a class="navigation-links" href="./catalog">Catalog</a>
     </nav>
     <div class="sdc_detail_view"></div>
   </sdc-navigator>

Important conventions:

- The main render target must contain a ``.sdc_detail_view`` element.
- Links handled by the navigator use the ``navigation-links`` class.
- Relative controller paths use ``.``, ``..``, and ``*`` segments.
- Controller arguments are appended after ``~&``, for example
  ``/~catalog~detail~&model=Book&pk=7``.
- When the navigator loads a target controller named ``catalog``, it injects a
  custom element named ``<catalog_sdc-navigation-client>``. In practice, that
  means the page controller should extend ``SdcNavigationClientController``.

The navigator keeps browser history in sync with the controller path and
rebuilds breadcrumbs from the loaded page controllers by calling each page
controller's ``controller_name()`` method.

Page controllers with ``sdc-navigation-client``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``SdcNavigationClientController`` as the base for controllers that live
inside the navigator. Its main job is to confirm that the page finished loading
and to provide access back to the current navigator instance.

Example:

.. code-block:: javascript

   import {SdcNavigationClientController} from "sdc_tools";

   export class CatalogController extends SdcNavigationClientController {
     onInit() {
       this.menu_id = 2;
     }

     controller_name() {
       return "Catalog";
     }
   }

After ``willShow()``, the base class triggers ``navLoaded`` and ``changeMenu``.
That is how the navigator knows which controller is active and which menu group
to highlight.

List, detail, and search controllers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``sdc-list-view`` expects a model name or a queryset source in ``onInit()`` and
renders ``model.listView()`` into ``.list-container``.

.. code-block:: html

   <sdc-list-view data-model="Book"></sdc-list-view>

Supported ``onInit(model, filter, onUpdate)`` inputs:

- ``model``: model name or preconfigured model/query source
- ``filter``: plain object or callback returning a filter object
- ``onUpdate``: callback invoked after the underlying queryset refreshes

``sdc-detail-view`` loads exactly one model instance and requires both
``data-model`` and ``data-pk`` when the controller was not initialized with a
model object directly.

.. code-block:: html

   <sdc-detail-view data-model="Book" data-pk="7"></sdc-detail-view>

``sdc-search-view`` is meant to be nested inside a parent controller such as
``sdc-list-view``. It wraps the search form, normalizes field values into a
detached form instance, and then calls ``this._parentController.onSearch(form)``.

Minimal example:

.. code-block:: html

   <sdc-search-view data-range-size="10"
                    data-range-start="1"
                    data-range-end="10"
                    data-total-count="42">
     {% csrf_token %}
     {% include "elements/inline_form.html" with form=search_form %}
   </sdc-search-view>

To participate in automatic updates, searchable form inputs should use the
``timer-change`` class. ``sdc-search-view`` is registered with the
``sdc-update-on-change`` mixin, so typing pauses trigger ``onChange()`` after a
short debounce.

Model form workflow
^^^^^^^^^^^^^^^^^^^

``sdc-model-form`` wraps the standard generated form flow for SDC models. It
supports both create and edit modes:

- Edit mode is selected when ``pk`` is present or when the passed model already
  has a primary key.
- Create mode is selected when no ``pk`` is provided.
- Named forms are supported through the ``form_name`` argument.

Common parameters from ``onInit(...)``:

- ``model``: model name or a model instance
- ``pk``: primary key for edit mode
- ``next``: controller path to navigate to after a successful save
- ``filter``: queryset filter passed to ``querySet()``
- ``on_update`` and ``on_error``: optional callbacks
- ``form_header`` and ``button_text``: UI labels
- ``form_name``: generated named form variant
- ``reset_on_save``: clear form after create
- ``editing_after_save``: convert create form into edit mode after save
- ``auto_save``: if true, edit mode submits automatically on change

Example:

.. code-block:: html

   <sdc-model-form
       data-model="Book"
       data-next=".."
       data-form-header="Create Book"
       data-reset-on-save="true">
   </sdc-model-form>

When autosave is disabled for edit mode, the controller renders an explicit
submit button. On successful save it can stay on the current page, reset, or
emit ``goTo`` for the configured next controller path.

Feedback and helper controllers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``sdc-auto-submit`` intercepts submits from ``.ajax-form`` elements and routes
them through ``submitForm(form)``. It clears field errors on success, maps
server-rendered error HTML back into the form on failure, and emits either
``pushMsg`` or ``pushErrorMsg``.

``sdc-alert-messenger`` listens for those two events globally and appends a
temporary message row into ``.alert_msg_container``. Messages disappear
automatically after two seconds.

``sdc-search-select`` provides a reusable searchable selector. Its main
configuration options are:

- ``name``: submitted field name
- ``required``: if true, single-select values cannot be removed
- ``value``: initial selected values
- ``modelName``: optional model used to fetch options dynamically
- ``multiple``: enables multi-select mode
- ``ids``: optional ``pk__in`` restriction for model-backed options

The controller stores the chosen values in hidden inputs with the
``timer-change`` class, so it integrates naturally with ``sdc-update-on-change``
and search or autosave forms.
