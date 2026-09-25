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

The package entry point (``sdc_client``, ``src/index.js``) exports:

.. code-block:: javascript

   import {
     app, AbstractSDC, SdcModel, SdcQuerySet, registerModel,
     on, trigger, allOff, setEvent,
     setErrorsInForm, clearErrorsInForm, checkIfParamNumberBoolOrString,
     controllerFactory, runControlFlowFunctions, socketReconnect, test_utils,
   } from "sdc_client";

``app``
   Global runtime object. See `The app object`_.

``AbstractSDC``
   Base class for browser controllers. See :doc:`sdc_controller`.

``SdcModel`` and ``SdcQuerySet``
   Model and queryset classes for live server-backed data. See :doc:`sdc_model`.

``registerModel(name, classObj)``
   Registers a client model class under a model name. Querysets use this
   registry to instantiate their objects. The generated file
   ``Assets/src/models/src.js`` (``python manage.py sdc_make_model_js``) calls
   it for every SDC model.

``on(name, controller)``
   Subscribes a controller (or any object) to an application event. See
   `Application event bus`_.

``trigger(name, ...args)``
   Emits an application event. Returns a promise of the handler results.

``allOff(controller)``
   Removes the controller from all application event subscriptions.

``setEvent(name, functionName = name)``
   Maps an application event to a handler method name.

``setErrorsInForm($form, $resForm)``
   Copies the validation errors of a server-rendered form (``$resForm``) into
   the displayed form ``$form``: it moves ``.non-field-errors`` after
   ``.hidden-form-fields``, marks the matching ``.form-group.<auto-id>``
   elements with ``has-error``, appends their ``.alert-danger`` messages, and
   replaces file inputs. Returns ``true`` if the response contains no errors.

``clearErrorsInForm($form)``
   Removes the ``has-error`` classes, ``.alert-danger`` messages, and
   ``.non-field-errors`` from a form.

``checkIfParamNumberBoolOrString(value, controller = null)``
   Converts a string from the DOM into a JavaScript value: ``"true"``/``"false"``
   become booleans, ``"undefined"`` becomes ``undefined``, ``"none"`` (any
   case) becomes ``null``, integers and floats become numbers, and quoted
   strings lose their quotes. If ``controller`` has a property with that name,
   the property is returned instead (a method is returned bound to the
   controller). Non-string values are returned unchanged. The runtime uses it
   for ``this.params``, passing the parent controller, so
   ``data-on-update="reloadList"`` yields the parent's ``reloadList`` method.

``controllerFactory(parentController, $element, tagName, superTagNameList)``
   Low-level: creates the controller instance for a registered tag element,
   including mixins, parent link, ``$container`` and ``params``. For a global
   controller it returns the existing singleton. Normally called only by the
   runtime.

``runControlFlowFunctions(controller, process)``
   Low-level: runs the lifecycle of a created controller (load HTML,
   ``onLoad()``, child controllers, ``willShow()``, refresh). Returns a promise,
   which resolves immediately if ``controller.load_async`` is true.

``socketReconnect()``
   Closes the server-call WebSocket if ``SERVER_CALL_VIA_WEB_SOCKET`` is
   enabled. The socket reconnects automatically after one second. Does nothing
   with the HTTP transport.

``test_utils``
   Helpers for Jest tests: ``get_controller(tagName, initArguments, html)``,
   ``controllerFromTestHtml(html, afterLifecycle)``, ``getCsrfToken()``,
   ``login(user)``, and ``logout()``. See :doc:`testing`.

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
- The method may return HTML, a jQuery object, or a promise of either. JSX
  also works, see `JSX with sdcDom`_.
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

.. _sdc-client-app:

The app object
--------------

``app`` is a single object shared by the whole page.

Registration and bootstrap
^^^^^^^^^^^^^^^^^^^^^^^^^^

``app.register(Controller, overwrite = false)``
   Registers a controller class under the tag name from
   ``app.controllerToTag(Controller)`` and returns ``{ addMixin(...mixins) }``.
   ``addMixin`` accepts tag names (``"sdc-model-form"``) or controller classes.
   If the tag is already registered and ``overwrite`` is false, the call is
   ignored and ``addMixin`` does nothing.

``app.registerGlobal(Controller)``
   Registers the controller and marks it as global. ``app.init_sdc()`` creates
   one instance of it outside the page body (child of
   ``app.globalRootController``), even if the tag does not appear in the page.
   The instance is a singleton stored as ``window[camelCaseTagName]``, for
   example ``window.sdcAlertMessenger`` for ``<sdc-alert-messenger>``. If the tag
   also appears in the page, the same instance is reused and its
   ``$container`` is set to the new element. ``registerGlobal`` returns nothing,
   so global controllers cannot get mixins through ``addMixin``.

   .. note::

      Each further ``app.init_sdc()`` call creates new detached elements for
      the global tags. The singleton moves its ``$container`` to the new
      element and runs its lifecycle again, except ``onLoad()``.

``app.controllerToTag(Controller)``
   Returns the tag name for a class: upper-case letters become ``-`` plus the
   lower-case letter, digit groups get a leading ``-``, and a trailing
   ``-controller`` is removed (``UserListController`` → ``user-list``,
   ``Page2`` → ``page-2``).

``app.init_sdc()``
   Starts the runtime (see `Bootstrap flow`_) and returns a promise that
   resolves when all controllers are loaded. Calling it again scans the body
   for new controller tags (including tags registered in the meantime).

``app.updateJquery()``
   Installs ``$.fn.safeRemove``, ``$.fn.safeEmpty`` and ``$.fn.safeReplace``.
   Called by the first ``init_sdc()``.

``app.cleanCache()``
   Clears the cached controller HTML fragments of all tags.

``app.rootController`` and ``app.globalRootController``
   Plain ``AbstractSDC`` instances created by the first ``init_sdc()``. They
   are the parent controllers of the top-level controllers in the page body and
   of the global controllers.

Controller and DOM helpers
^^^^^^^^^^^^^^^^^^^^^^^^^^

``app.getController($elem)``
   Returns the controller bound to ``$elem`` or to its closest controller
   ancestor element, or ``undefined``.

``app.safeRemove($elem)``, ``app.safeEmpty($elem)``, ``app.safeReplace($elem, $new)``
   Function form of the safe jQuery helpers (see `Safe DOM operations`_).
   ``safeReplace`` inserts ``$new`` before ``$elem`` and then safely removes
   ``$elem``.

``app.refresh($dom, leafController = null)``
   Instantiates new controller tags inside ``$dom``, re-renders the
   ``<this.*>`` placeholders of ``leafController`` inside ``$dom``, re-wires the
   events and runs ``onRefresh(leafController)`` on ``leafController`` and its
   ancestor controllers. Without ``leafController`` the controller of ``$dom``
   is used. ``controller.refresh()`` calls it.

``app.reloadController(controller)``
   Loads the controller HTML again (see ``reload()`` in :doc:`sdc_controller`)
   and reconciles it into the controller element.

``app.reconcile(controller, $virtualNode, $realNode = null, process = null)``
   Renders ``$virtualNode`` (controllers and placeholders) and merges it into
   ``$realNode``, keeping matching DOM nodes. Without ``$realNode`` the new
   content replaces the content of ``controller.$container``. Resolves with the
   controller.

HTTP helpers
^^^^^^^^^^^^

``app.get(controller, url, args)`` and ``app.post(controller, url, args)``
   Send ``args`` with ``$.get`` or ``$.post``. The runtime adds ``VERSION`` and
   ``_method: "api"`` to ``args`` (and ``CSRF_TOKEN`` for ``post``). On the
   server, ``_method=api`` routes the request to the ``get_api()`` or
   ``post_api()`` method of the ``SDCView``. The promise resolves with the
   response body. If the body has ``status: "redirect"``, the runtime triggers
   ``onNavLink`` with ``body["url-link"]``; otherwise it refreshes
   ``controller.$container`` after the ``then`` callbacks attached to the
   returned promise have run.

``app.ajax(controller, url, args, method)``
   Shared implementation of ``get`` and ``post``; ``method`` is ``$.get`` or
   ``$.post``.

``app.submitFormAndUpdateView(controller, form, url, method)``
   Sends ``new FormData(form)`` (including files) to ``url`` or
   ``form.action`` with ``method`` or ``form.method``. Non-GET requests carry
   the ``X-CSRFToken`` header. While uploading, the runtime shows
   ``.progress-container`` elements and sets the width and text of their
   ``.progress-bar``. A response with ``status: "redirect"`` or HTTP status 301
   (``send_redirect()`` on the server) triggers ``onNavLink`` with
   ``url-link``, or sets ``window.location.href`` to ``url`` when there is no
   ``url-link``; a 301 response resolves the promise. Other responses refresh
   the controller. ``controller.submitForm()`` calls this function.

``app.submitForm(form, url, method)``
   Same request as above, without refresh and without redirect handling.

.. note::

   ``app.get()`` and ``app.post()`` react only to a successful response whose
   body has ``status: "redirect"``. A ``send_redirect()`` response has HTTP
   status 301, so it rejects the promise and no navigation happens. Use
   ``submitForm()`` if the server answers with ``send_redirect()``.

Values read from ``window``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The generated ``base.html`` template sets these globals before the bundle is
loaded:

``app.CSRF_TOKEN``
   ``window.CSRF_TOKEN`` (default ``""``). Sent by ``app.post()``. The
   form-upload and server-call requests read ``window.CSRF_TOKEN`` directly.

``app.LANGUAGE_CODE``
   ``window.LANGUAGE_CODE`` (default ``"en"``).

``app.DEBUG``
   ``window.DEBUG`` (default ``false``). If true, lifecycle calls are logged
   with ``console.debug``.

``app.VERSION``
   ``window.VERSION`` (default ``"0.0"``). Sent with every content and API
   request.

``window.SERVER_CALL_VIA_WEB_SOCKET``
   Not copied to ``app``; read on each server call to choose between HTTP and
   WebSocket (see :doc:`sdc_controller`).

The ``app`` values are read once, when the client module is imported. Changing
``window.DEBUG`` later has no effect on ``app.DEBUG``.

.. _sdc-client-jsx:

JSX with ``sdcDom``
-------------------

The client defines a global JSX factory, ``window.sdcDom``. Generated projects
compile JSX with Babel's classic React runtime and this pragma
(``Assets/babel.config.json``):

.. code-block:: json

   {
     "presets": [
       ["@babel/preset-react", { "runtime": "classic", "pragma": "sdcDom" }]
     ]
   }

``sdcDom(tag, props, ...children)`` returns a jQuery element, not a virtual
node, so JSX can be returned from ``<this.*>`` placeholder methods or appended
with jQuery:

- A string ``tag`` creates that element. A falsy ``tag`` returns ``""``.
- A function ``tag`` (for example ``<this.row data-pk={7} />``) creates a
  ``<this.row>`` placeholder bound to that function. On refresh the function
  is called with the controller as ``this`` and the placeholder's ``data-*``
  values, like a placeholder written in the template.
- ``className`` becomes ``class``. Other props are set with
  ``setAttribute()``, so values are converted to strings.
- Props starting with ``on`` (``onClick``) are attached with
  ``addEventListener()`` using the lower-cased rest of the name (``click``).
  They are native listeners, so ``this`` is not the controller; use arrow
  functions.
- Children (strings, jQuery objects, arrays of them) are appended in order.

.. code-block:: jsx

   class TodoList extends AbstractSDC {
     // <this.items></this.items> in the controller template
     items() {
       return (
         <ul>
           {this.todos.map((t) => (
             <li sdc_click="toggle" data-id={t.id} className={t.done ? "done" : ""}>
               {t.title}
             </li>
           ))}
         </ul>
       );
     }

     toggle($li, event) {
       // ...
       this.refresh();
     }
   }

The ``sdc_tools`` controllers use this style: JSX for the markup and
``sdc_click`` attributes for events.

.. note::

   Placeholder output is reconciled into the DOM. When a rendered node matches
   an existing node, the existing node is kept and only its attributes and
   jQuery data are updated. Listeners from ``on*`` props are attached to the
   newly created node only, so a kept node keeps the listener from the render
   in which it was first inserted. ``sdc_<event>`` attributes do not have this
   problem, because they are read when the event happens.

.. _sdc-client-event-bus:

Application event bus
---------------------

The event bus connects controllers without DOM coupling. Events are names;
subscribers are objects (normally controllers) that implement a handler
method.

``setEvent(name, functionName = name)``
   Defines which method handles ``name``. Only the first definition of a name
   is used; later calls for the same name are ignored.

``on(name, controller)``
   Subscribes ``controller``. It calls ``setEvent(name)`` first, so the method
   name defaults to the event name; call ``setEvent(name, "otherMethod")``
   before the first ``on()`` for a different method. If the controller has no
   such method, a message is logged and it is not subscribed. Subscribing the
   same controller twice calls it twice.

``trigger(name, ...args)``
   Calls the handler method of every subscriber synchronously, in subscription
   order, with ``args``. Returns ``Promise.all()`` of the non-``undefined``
   return values, so handlers can return promises. An exception in a handler
   is thrown from ``trigger()`` itself. If the event name was never defined,
   the promise resolves to ``undefined``.

``allOff(controller)``
   Unsubscribes the controller from all events. ``controller.remove()`` calls
   it, so removed controllers are unsubscribed automatically.

.. code-block:: javascript

   import { on, setEvent, trigger } from "sdc_client";

   class Cart extends AbstractSDC {
     onLoad($html) {
       setEvent("itemAdded", "handleItemAdded");
       on("itemAdded", this);
       return super.onLoad($html);
     }

     handleItemAdded(item) {
       return this.refresh();
     }
   }

   // elsewhere
   trigger("itemAdded", { id: 3 }).then((results) => { /* ... */ });

Events used by the runtime and ``sdc_tools``:

- ``pushMsg(header, msg)`` and ``pushErrorMsg(header, msg)``: status messages
  from server calls (shown by ``sdc-alert-messenger``).
- ``onNavLink(link)``: redirects from API, form and server-call responses
  (handled by ``sdc-navigator``).
- ``_RedirectOnView(link)``: a controller HTML request was answered with a
  301 redirect.
- Server-side ``sdc_event`` messages on the server-call WebSocket are
  re-triggered as ``trigger(event, payload)``.

.. _sdc-client-dom-events:

DOM event dispatch
------------------

The runtime does not bind handlers to individual elements. ``init_sdc()`` adds
one listener on ``window`` for every standard event type (all ``on*`` keys of
``window`` except ``beforeunload`` and ``unload``). For each event it walks from
``event.target`` up through the DOM ancestors. At every element with an
``sdc_<type>`` attribute (``sdc_click``, ``sdc_submit``, ``sdc_keydown`` …) it:

1. finds the controller of that element (its closest controller),
2. splits the attribute value at spaces into method names,
3. calls each name that is a method of the controller as
   ``method.call(controller, $elem, event)``,
4. repeats steps 2–3 for the parent controller, its parent, and so on up to
   the root controller.

So a method is called on every controller in the chain that defines it, and
elements higher in the DOM with their own ``sdc_<type>`` attribute are handled
afterwards in the same way.

.. code-block:: html

   <button sdc_click="validate save">Save</button>

The runtime replaces ``stopPropagation()`` and ``stopImmediatePropagation()``
on the event object:

``event.stopPropagation()``
   Skips the remaining method names and stops the dispatch completely.

``event.stopImmediatePropagation()``
   Lets the remaining method names of the current controller run, then stops
   the dispatch.

Neither calls the browser's native method. ``event.preventDefault()`` works as
usual.

Handlers from the ``events`` map of a controller use the same mechanism: after
each refresh the runtime adds ``this.event_<selector>`` to the ``sdc_<type>``
attribute of every matching element inside the controller. Elements added to
the DOM without a refresh do not get these entries until the next refresh.

Further details:

- ``mouseenter``, ``mouseleave`` and ``mouseout`` handlers run
  only when the element under the pointer is outside the element.
- Custom event types are registered on the fly: ``init_sdc()`` wraps
  ``$.fn.trigger``, and the first ``$elem.trigger("itemmoved")`` adds a window
  listener for ``itemmoved``, so ``sdc_itemmoved`` attributes work. Use
  lower-case event names, because HTML attribute names are lower-cased. Custom events
  dispatched with the native ``dispatchEvent()`` are not registered this way.
- For namespaced jQuery events the attribute name includes the namespace
  (``sdc_saved.form`` for ``trigger("saved.form")``).

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
