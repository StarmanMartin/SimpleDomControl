First App
=========

We want to create a library app.
A library has books that can be borrowed online. However, each book can only be borrowed once.

By the end you will have touched every core part of SDC: controllers, DOM events,
server calls, live-syncing models, forms, navigation, and permissions.

.. note::

   **Prerequisites:** Python ≥ 3.13, Django ≥ 6.0, Node ≥ 18, and basic familiarity
   with Django (apps, models, migrations). You do **not** need a frontend framework —
   SDC *is* the frontend.

The one idea to hold onto
-------------------------

**Every UI piece in SDC is a pair:** a server-side ``SDCView`` (renders an HTML
fragment, runs permissions, exposes callable methods) and a client-side
``AbstractSDC`` controller (loads that fragment, binds events, manages children,
talks back to the server). They share a name and are joined by a **custom HTML
tag**::

    controller "catalog"  ─►  server class Catalog(SDCView)   (renders the fragment)
                          ─►  client class CatalogController   (drives the DOM)
                          ─►  used in markup as  <catalog></catalog>

The CLI generates both halves for you and keeps URLs and the JS build in sync.
You mostly fill in behavior. The naming map is fixed:

- controller name is ``snake_case`` (``my_list``)
- → JS class ``MyListController`` → server class ``MyList``
- → HTML tag ``<my-list>`` → ``contentUrl = "/sdc_view/main_app/my_list"``

Project setup
-------------

First we need to create a new project. Therefore, cd into the development directory.

.. code-block:: sh

    PROJECT_NAME=Library
    pip install django
    django-admin startproject $PROJECT_NAME
    cd ./$PROJECT_NAME
    virtualenv venv
    source venv/bin/activate
    pip install simpledomcontrol
    sed -i "s/INSTALLED_APPS = \[/INSTALLED_APPS = ['sdc_core',/g" ./$PROJECT_NAME/settings.py
    python manage.py sdc_init
    npm install

This creates a new folder named Library in your development directory. This directory is the new root project directory. It contains a Django project with all SDC extensions.

In order not to forget it, we should carry out the migration right away and create a super user.

.. code-block:: sh

    python manage.py migrate
    python manage.py createsuperuser

In the next step we need to create a new Django app. We call it *main_app*:

.. code-block:: sh

    python manage.py startapp main_app

Do not forget to add *main_app* to the installed apps:

.. code-block:: python

    ...
    INSTALLED_APPS = ['daphne'] + INSTALLED_APPS + ['channels', 'sdc_tools', 'sdc_user', 'main_app']
    ...

*./Library/Library/settings.py*

Now that the *main_app* has been created, we can add a new SDC controller to the app. We call the controller *dashboard*:

.. code-block:: sh

    python manage.py sdc_cc

New Controller
--------------
This is followed by the following CLI prompts:

.. code-block:: sh

    Enter number to select an django App:
    1 -> main_app
    Enter number: [1] 1
    Enter the name of the new controller (use snake_case): dashboard

The sdc_cc command creates the following files and links:

::

    └─ your_chosen_directory/
       └─ Library/
          ├─ Assets/
             ├─ src
                ├─ main_app -> ../../main_app/Assets/src/main_app
                └─ ...
             └─ ...
          ├─ main_app
            ├─ templates
                └─ main_app
                    └─ sdc
                        └─ dashboard.html
             ├─ Assets/
                ├─ src
                    └─ main_app
                        ├─ controller
                            └─ dashboard
                                ├─ dashboard.html  -> ../../../../../templates/main_app/sdc/dashboard.html
                                ├─ dashboard.js
                                └─ dashboard.scss
                        ├─ main_app.organizer.js
                        └─ main_app.organizer.scss
                 └─ ...
          ├─ Library
             └─ ...
          └─ ...


Next, we will add two more controllers: the 'catalog' controller and the 'my_list' controller.

.. code-block:: sh

    python manage.py sdc_cc -a main_app -c catalog
    python manage.py sdc_cc -a main_app -c my_list

These two commands are equivalent to the dashboard controller and generate JS, SCSS and HTML files for both controllers.
Before we work with the two two controllers we set up the in app navigation.

Basic Navigation
----------------

Let us fist add the dashboard controller as default view to the main navigation.

.. code-block:: html

    ...
    <!-- nav view controller ind sdc_tools -->
    <!-- TODO: data-default-controller sets the default view -->
    <sdc-navigator data-default-controller="dashboard">
    ...

*./Library/templates/index.html*

Next we need to edit the HTML file of the *dashboard* controller:

.. code-block:: html

    <div class="d-flex">
        <h2>Dashboard</h2>
        <div class="ms-auto">
            {% if user.is_authenticated %}
                <p class="mb-1">Hello: {{ user.get_username }}</p>
                <sdc-logout></sdc-logout>
            {% else %}
                <a class="btn btn-info navigation-links" href="/sdc-login">Login</a>
            {% endif %}
        </div>
    </div>

    <div class="container-fluid">
        <div class="row">
            <div class="col-3">
                <h3>Menu</h3>
                <p><a class="navigation-links" href="/*/catalog">Catalog</a></p>
                <p><a class="navigation-links" href="/*/my-list">My List</a></p>
            </div>
            <div class="col">
                <!-- Add a new sub container for navigation controller -->
                <div class="sdc_detail_view" data-default-controller="catalog"></div>
            </div>
        </div>
    </div>


*./Library/main_app/templates/main_app/sdc/dashboard.html*

If you reload the page now, you will see that there is a basic navigation bar on the left-hand side of the page, containing two links and a main view of the catalog controller content.


.. include:: snippets/basic_navigation.rst

see more: :ref:`sdc-how-to-nav`


DB Model
--------

Now that navigation through the available pages has been implemented, the next
step is to fill the pages with content. To do this, we first need to create a
new database table. For this, we will use an extension of the Django ORM
(Object-Relational Mapper). In SDC, these model classes do not need to be
created manually. This can be done with a simple SDC command.

.. code-block:: sh

    python manage.py sdc_new_model -a main_app -m Book

This command generates the following:

1. A new model class named Book in:

    - ./Library/main_app/models.py

2. A new form class named BookForm in:

    - ./Library/main_app/forms.py

3. Two new HTML view templates for the Book model:

    - ./Library/Assets/src/main_app/models/Book/Book_details.html
    - ./Library/Assets/src/main_app/models/Book/Book_list.html

see more: :ref:`new-model-label`

Now, we need to populate. In this example, a book has a title, an author, text and a user relation field called 'borrowed by'.

.. include:: snippets/book_model.rst

In SDC, the model is responsible for managing its own access rights. To ensure secure authorisation, edit the 'is_authorised' method.

.. warning::

   **Models are deny-by-default.** ``SdcModel.is_authorised()`` and
   ``get_queryset()`` have **no usable defaults** — ``is_authorised`` returns
   ``False`` and ``get_queryset`` raises. A model that does not override **both**
   is fully closed and every action on it is forbidden. This is deliberate. Always
   provide both methods.

.. code-block:: python

    ...
    class Book(models.Model, SdcModel):
        ...
        @classmethod
        def is_authorised(cls, user, action, obj):
            match action:
                case 'connect':
                    return True
                case 'list_view':
                    return True
                case 'detail_view':
                    return True
                case 'load':
                    return True
                case _: # edit_form, named_form, create_form, save, create, upload, delete
                    return False

        # Which rows this user may see/operate on, per action.
        @classmethod
        def get_queryset(cls, user, action, obj):
            return cls.objects.all()
    ...

*./Library/main_app/models.py*

Since we do not need the forms for the books (User can not alter or create books),
the Form classes can be ignored in this case. First, we should take care of the
representation in the client.

Client-Side Data Models
-----------------------

The user should be able to browse the books as a list and read a details of the individual books. SDC offers a ListView and a DetailView for the client for this purpose.

.. code-block:: html

    {% load sdc_filter %}

    <div class="search-view-container">
        <sdc-search-view
                data-range-size="{{ range_size }}"
                data-range-start="{{ range|indexfilter:0 }}"
                data-range-end="{{ range|indexfilter:1 }}"
                data-total-count="{{ total_count }}"
                data-remove-labels="true">
            {% csrf_token %}
            {% include "elements/inline_form.html" with form=search_form %}
        </sdc-search-view>
    </div>

    {% if template_context.my_list %}
        <h3>All books you have borrowed!</h3>
    {% endif %}
    <table class="table">
        <tbody>
        {% for instance in instances %}
            <td>
                <this.borrow_btn data-instance="{{ instance|serialize }}" data-user="{{ user.id }}"></this.borrow_btn>
            </td>
            <td>
                <b>{{ instance.title }}</b><br>
                by: {{ instance.author }}
            </td>
            <td>
                <a class="btn btn-info navigation-links"
                   href="/*/*/sdc-detail-view&model={{ instance|to_class_name }}&pk={{ instance.pk }}">More</a>
                <!-- Modal -->

            </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>

*./Library/Assets/src/main_app/models/Book/Book_list.html*

.. code-block:: html

    {% load sdc_filter %}

    <div class="container-fluid">
        <div class="row">
            <div class="col-4">
                <h3>{{instance.title}}</h3>
                <h3>by: {{instance.author}}</h3>
            </div>
            <div class="col-8">
                <p>{{instance.text}}</p>
            </div>
        </div>
    </div>

*./Library/Assets/src/main_app/models/Book/Book_details.html*

The list template contains two SDC concepts that go beyond plain Django
templating:

- ``<sdc-search-view>`` turns its inner Django form into a live search form
  (see :ref:`sdc-controller-label`). The ``range_size``, ``range``,
  ``total_count``, and ``search_form`` context variables are produced by the
  ``handle_search_form`` helper on the model's ``render()`` classmethod.
- ``<this.borrow_btn ...>`` is a *dynamic DOM fragment*. When the runtime
  refreshes the list, it calls the ``borrow_btn`` method on the current
  ``Catalog`` controller (we will add it below) and reconciles its return value
  back into the DOM.

Wiring up the Catalog
---------------------

The catalog page renders the book list. Since ``sdc_tools`` already ships a
generic ``sdc-list-view`` controller, the catalog template itself stays tiny:

.. code-block:: html

    <h2>Catalog</h2>

    <sdc-list-view data-model="Book"></sdc-list-view>

*./Library/main_app/templates/main_app/sdc/catalog.html*

``<sdc-list-view>`` reads ``data-model="Book"``, creates a client-side
``SdcQuerySet``, calls the model's ``list_view`` on the server, and drops the
rendered HTML into its ``.list-container`` child. After every ``save``,
``create``, or ``delete`` event on the queryset the list refreshes itself.

The JavaScript side of the controller only needs to declare which dynamic
fragments are used in the list template. We implement the ``borrow_btn``
handler on a dedicated ``catalog`` controller so the list template stays
framework-agnostic.

.. code-block:: javascript

    import {AbstractSDC, app, trigger} from 'sdc_client';

    class CatalogController extends AbstractSDC {
        constructor() {
            super();
            this.contentUrl = "/sdc_view/main_app/catalog";
        }

        onInit() {
            this.books = this.querySet('Book');
        }

        borrow_btn({instance, user}) {
            const isBorrowed = instance.borrowed_by != null;
            const isMine = instance.borrowed_by === user;
            if (isBorrowed && !isMine) {
                return `<span class="text-muted">borrowed</span>`;
            }
            const label = isMine ? 'Return' : 'Borrow';
            const action = isMine ? 'returnBook' : 'borrowBook';
            return `<button class="btn btn-primary"
                            sdc_click="${action}"
                            data-pk="${instance.pk}">${label}</button>`;
        }

        borrowBook(ev, $btn) {
            return this.serverCall('borrow', {pk: $btn.data('pk')});
        }

        returnBook(ev, $btn) {
            return this.serverCall('return', {pk: $btn.data('pk')});
        }
    }

    app.register(CatalogController);

*./Library/main_app/Assets/src/main_app/controller/catalog/catalog.js*

The ``sdc_click`` attribute is the declarative counterpart of the ``events``
map. Either one calls the method by name and passes ``(event, $element)``.
``serverCall(...)`` invokes a matching Python method on the server-side view
that we will add next.

Server methods on a controller view
-----------------------------------

``serverCall`` is dispatched to a method on the ``SDCView`` that serves the
controller. Methods must be named ``call_<name>`` (for synchronous calls) or
``call_async_<name>`` (for async calls).

.. code-block:: python

    from sdc_core.sdc_extentions.views import SDCView, SdcLoginRequiredMixin
    from django.shortcuts import render

    from main_app.models import Book


    class Catalog(SdcLoginRequiredMixin, SDCView):
        template_name = 'main_app/sdc/catalog.html'

        def get_content(self, request, *args, **kwargs):
            return render(request, self.template_name)

        def call_borrow(self, channel=None, pk=None, **kwargs):
            book = Book.objects.get(pk=pk)
            if book.borrowed_by_id is None:
                book.borrowed_by = channel.user
                book.save()
            return {'ok': True}

        def call_return(self, channel=None, pk=None, **kwargs):
            book = Book.objects.get(pk=pk)
            if book.borrowed_by_id == channel.user.id:
                book.borrowed_by = None
                book.save()
            return {'ok': True}

*./Library/main_app/sdc_views.py*

The ``channel`` argument exposes the current user and lets you redirect the
client programmatically. ``SdcLoginRequiredMixin`` (or
``SdcGroupRequiredMixin`` for group-based access) hides the controller from
anonymous visitors. See :ref:`sdc-controller-label` for the full list of
``AbstractSDC`` hooks available on the client.

A few things worth knowing about ``serverCall``:

- **The method name is matched verbatim.** ``serverCall('borrow', …)`` invokes a
  method named exactly ``call_borrow``. The ``call_`` prefix is a convention, not
  magic. Use ``async def call_async_<name>(self, channel=None, **kwargs)`` for
  async work.
- **Name guard (security):** method names that start with ``_`` or that collide
  with framework internals (``dispatch``, ``get_queryset``, ``is_authorised``, …)
  are rejected. Name your callables plainly.
- Returning a ``dict``/``list`` sends it straight back to the client's
  ``.then(...)``.

.. note::

   **HTTP vs WebSocket transport.** ``serverCall`` uses one transport for the whole
   app, chosen by a single flag — there is no per-call option. The default is
   **HTTP POST**. To send server calls (and model sync) over the WebSocket instead,
   set ``SERVER_CALL_VIA_WEB_SOCKET = True`` in ``settings.py``; SDC passes it into
   the page as ``window.SERVER_CALL_VIA_WEB_SOCKET`` in ``base.html``. Leave it
   ``False`` (the default) to use plain HTTP, which needs no ASGI/WebSocket wiring
   for the call itself.

Registering the model on the client
-----------------------------------

The generated ``Book`` model class needs to be available to the browser so
``querySet('Book')`` knows what to instantiate. ``sdc_new_model`` already wired
the import into the app organizer, but it is useful to see what that looks
like:

.. code-block:: javascript

    import {app, Model} from 'sdc_client';
    import './controller/dashboard/dashboard.js';
    import './controller/catalog/catalog.js';
    import './controller/my_list/my_list.js';

    class Book extends Model {
        static name = 'Book';
        // Extra client-only methods can be attached here.
    }
    app.registerModel(Book);

*./Library/main_app/Assets/src/main_app/main_app.organizer.js*

The client-side ``Book`` class mirrors the fields of the Django model. The
runtime synchronizes field values through ``syncForm()`` and
``syncModelToForm()`` so a given model instance and its form stay in lock step
(see :doc:`sdc_model`).

Live updates over WebSocket
---------------------------

``SdcQuerySet`` opens a WebSocket channel while it is alive. When another
browser updates a ``Book`` the matching queryset instance receives the event
and re-renders the list view automatically. No extra code is needed for the
catalog — ``sdc-list-view`` subscribes on your behalf.

To react to model pushes yourself, assign handlers to the queryset:

.. code-block:: javascript

    this.books.onUpdate = (book) => {
        trigger('pushMsg', `${book.title} was updated`);
    };
    this.books.onCreate = (book) => {
        trigger('pushMsg', `New book: ${book.title}`);
    };

The global ``pushMsg`` and ``pushErrorMsg`` events are picked up by the
``sdc-alert-messenger`` controller that ``sdc_tools`` injects into the shell.

The "My List" page
------------------

The "My List" page reuses ``sdc-list-view`` but narrows the queryset to the
current user. ``onInit(model, filter, onUpdate)`` accepts the filter as the
second argument.

.. code-block:: html

    <h2>My books</h2>

    <sdc-list-view
        data-model="Book"
        data-filter='{"borrowed_by": "{{ user.id }}"}'
        data-template-context='{"my_list": true}'>
    </sdc-list-view>

*./Library/main_app/templates/main_app/sdc/my_list.html*

``data-*`` attributes are parsed into native JavaScript values, so the
``data-filter`` JSON is delivered to ``onInit()`` as an object. The
``template_context`` payload is passed through to ``render()`` and is what the
``{% if template_context.my_list %}`` branch in ``Book_list.html`` keys off of.

Book details and modal navigation
---------------------------------

The catalog rows link to a detail page through a relative navigator path. The
``sdc_tools`` app ships a ready-made ``sdc-detail-view`` that only needs the
model name and primary key:

.. code-block:: html

    <!-- The link was generated in Book_list.html -->
    <a class="btn btn-info navigation-links"
       href="/*/*/sdc-detail-view&model=Book&pk={{ instance.pk }}">More</a>

Any ``<a>`` with the class ``navigation-links`` is intercepted by the navigator:
it cancels the browser navigation and calls ``goTo`` with the link's ``href``.
The ``href`` is an SDC path, not a real URL, and it carries client params as a
query string that arrive as ``onInit`` arguments on the target controller.

When the navigator resolves the link it injects a ``<sdc-detail-view
data-model="Book" data-pk="...">`` element into a nested ``sdc_detail_view``
container. The views of a path render into **nested** ``sdc_detail_view``
containers, so a deeper view opens *inside* its parent — give a view its own
``<div class="sdc_detail_view"></div>`` when you want children to nest below it,
and leave it out when a deeper link should replace the current view instead. If
the chosen placeholder carries ``data-modal="#myModal"`` the navigator opens the
matching Bootstrap modal, renders the detail view inside it, and closes the modal
(navigating back to the parent level) when it is dismissed — see
:ref:`sdc-how-to-nav` for the modal markup.

Editing books as staff
----------------------

So far users can only browse books. To allow staff members to create or edit
books, relax the authorization rules and add a model form. ``sdc-model-form``
wraps the generated ``BookForm`` and takes care of create vs. edit mode,
validation errors, and redirects.

First, widen the authorization so staff can edit:

.. code-block:: python

    @classmethod
    def is_authorised(cls, user, action, obj):
        if action in ('connect', 'load', 'list_view', 'detail_view'):
            return True
        if user.is_authenticated and user.is_staff:
            return action in ('edit_form', 'create_form',
                              'save', 'create', 'delete')
        return False

Then drop a form controller into an admin-only page:

.. code-block:: html

    <sdc-model-form
        data-model="Book"
        data-pk="{{ pk|default_if_none:'' }}"
        data-form-header="{% if pk %}Edit book{% else %}New book{% endif %}"
        data-next="..">
    </sdc-model-form>

*./Library/main_app/templates/main_app/sdc/book_edit.html*

``data-next=".."`` navigates one level up after a successful save. Other
supported options are covered in :ref:`sdc-controller-label`, including
``data-reset-on-save``, ``data-auto-save``, and ``data-editing-after-save``.

If a controller needs its own behavior on top of the generic form, register it
as a mixin:

.. code-block:: javascript

    import {AbstractSDC, app} from 'sdc_client';

    class BookEditController extends AbstractSDC {
        constructor() {
            super();
            this.contentUrl = "/sdc_view/main_app/book_edit";
        }

        onInit() {
            this.model_name = 'Book';
        }

        titleUpper() {
            this.model.title = (this.model.title || '').toUpperCase();
        }
    }

    app.register(BookEditController, false).addMixin('sdc-model-form');

*./Library/main_app/Assets/src/main_app/controller/book_edit/book_edit.js*

Mixing in ``sdc-model-form`` adds its event map and submit pipeline to the
concrete controller. ``this.model`` on the mixin is the bound ``SdcModel``
instance — mutating it is enough, because the form fields stay in sync.

Named forms
-----------

A model can expose several forms. Declare each one in ``SdcMeta`` and select
it per controller with ``data-form-name``:

.. code-block:: python

    class SdcMeta:
        edit_form = "main_app.forms.BookForm"
        create_form = "main_app.forms.BookForm"
        small = "main_app.forms.SmallBookForm"
        html_list_template = "main_app/models/Book/Book_list.html"
        html_detail_template = "main_app/models/Book/Book_details.html"

.. code-block:: html

    <sdc-model-form data-model="Book"
                    data-pk="{{ pk }}"
                    data-form-name="small"></sdc-model-form>

You can also select a named form through a navigator link with a ``form_name``
query parameter, which arrives as an ``onInit`` argument:

.. code-block:: html

    <a class="navigation-links"
       href="./sdc-model-form?model=Book&pk={{ instance.pk }}&form_name=small&next=..">Quick edit</a>

The server looks the name up on ``SdcMeta`` and falls back to ``edit_form`` if it
is not found, so an unknown name is safe. The chosen form name is remembered on
the form and sent back on save, so edits go through the same named form.

Feedback and auto-submitting forms
----------------------------------

The ``sdc-alert-messenger`` controller displays short-lived notifications from
the ``pushMsg`` and ``pushErrorMsg`` events. ``sdc_init`` already adds it to
``base.html``; you can fire messages from anywhere:

.. code-block:: javascript

    import {trigger} from 'sdc_client';
    trigger('pushMsg', 'Saved!');
    trigger('pushErrorMsg', 'Something went wrong');

For classic Django forms that do not need the full model pipeline, add the
``ajax-form`` class and ``sdc-auto-submit`` takes over: it intercepts submit,
posts over AJAX, maps server-rendered field errors back, and emits ``pushMsg``
or ``pushErrorMsg`` automatically.

.. code-block:: html

    <form class="ajax-form" action="{% url 'contact' %}" method="post">
        {% csrf_token %}
        {{ form }}
        <button class="btn btn-primary" type="submit">Send</button>
    </form>

Login, logout and groups
------------------------

The ``sdc_user`` app ships ready-made login, register, and logout controllers.
The dashboard template used ``<sdc-logout>`` and ``/sdc-login`` — both are
provided by ``sdc_user`` out of the box. To restrict a page to logged-in users
or to a group, use the server-side mixins:

.. code-block:: python

    from sdc_core.sdc_extentions.views import (SDCView, SdcLoginRequiredMixin,
                                               SdcGroupRequiredMixin)

    class MyList(SdcLoginRequiredMixin, SDCView):
        template_name = 'main_app/sdc/my_list.html'
        raise_exception = True

        def get_content(self, request, *args, **kwargs):
            return render(request, self.template_name)


    class AdminOnly(SdcGroupRequiredMixin, SDCView):
        group_required = ['Editor']
        staff_allowed = True    # defaults to False — opt in to allow staff
        template_name = 'main_app/sdc/admin_only.html'

        def get_content(self, request, *args, **kwargs):
            return render(request, self.template_name)

.. warning::

   ``staff_allowed`` defaults to **False** on group-required views. If you want any
   staff user to pass a group-gated view, set ``staff_allowed = True`` explicitly.
   Likewise, set ``raise_exception = True`` to return a ``403`` instead of
   redirecting to the login flow.

Unauthorized requests are redirected to the login flow. On the client the
``login`` and ``logout`` application events are broadcast so any controller can
react — for example to hide admin menu entries.

URL parameters and ``sdc_update_url``
-------------------------------------

Detail pages frequently take a primary key in their URL. Edit
``main_app/sdc_urls.py`` to add a parameter:

.. code-block:: python

    urlpatterns = [
        path('book_edit/<int:pk>', sdc_views.BookEdit.as_view(),
             name='scd_view_main_app_book_edit'),
    ]

Then regenerate the JavaScript ``contentUrl`` with:

.. code-block:: sh

    python manage.py sdc_update_url

After running the command the controller's ``contentUrl`` becomes
``/sdc_view/main_app/book_edit/%(pk)s`` and the tag is rendered with
``data-pk``. See :ref:`sdc-how-to-nav` for how to pass these values through
the navigator.

Lifecycle recap
---------------

Every controller goes through the same lifecycle, which is worth reading
alongside :ref:`sdc-controller-label`:

1. ``constructor`` — define ``contentUrl`` and event maps.
2. ``onInit(...)`` — receive ``data-*`` attributes.
3. ``onLoad(html)`` — mutate the freshly-fetched HTML before nested
   controllers load.
4. ``willShow()`` — run once children are ready but before the first refresh.
5. ``onRefresh()`` — called every time ``refresh()``/``reload()`` runs.
6. ``onRemove()`` — cleanup; return ``false`` to cancel removal.

A minimal annotated controller for the dashboard:

.. code-block:: javascript

    import {AbstractSDC, app} from 'sdc_client';

    class DashboardController extends AbstractSDC {
        constructor() {
            super();
            this.contentUrl = "/sdc_view/main_app/dashboard";
            this.events.unshift({
                click: {
                    '.refresh-btn': 'refresh',
                },
            });
        }

        onInit(welcome = 'Welcome') {
            this.welcome = welcome;
        }

        onLoad($html) {
            $html.find('.heading').text(this.welcome);
            return super.onLoad($html);
        }

        onRefresh() {
            return super.onRefresh();
        }
    }

    app.register(DashboardController);

Safe DOM updates
----------------

When removing or replacing parts of the DOM that contain SDC controllers, use
the safe helpers instead of raw jQuery operations so child controllers, model
connections, and events are torn down cleanly:

.. code-block:: javascript

    this.$container.find('.old-section').safeRemove();
    this.$container.find('.slot').safeReplace($newFragment);

Testing the app
---------------

``sdc_init`` scaffolds a Jest test setup under ``Assets/tests``. A controller
test usually renders its tag and asserts on the resulting DOM or on state
changes:

.. code-block:: javascript

    import {app} from 'sdc_client';
    import '../src/main_app/controller/catalog/catalog.js';

    test('catalog borrow button toggles label', async () => {
        const $root = $('<catalog></catalog>').appendTo('body');
        await app.init_sdc();
        // ... assert against the rendered list container.
    });

The Django side can be tested with the regular test runner. Server-call
methods and authorization rules are plain Python and do not need WebSocket
plumbing to be exercised.

General styling and HTML header
-------------------------------

Let us now add a background images and a favicon to the static directory:

::

    └─ your_chosen_directory/
       └─ Library/
          ├─ Assets/
             ├─ static
                ├─ favicon.png
                └─ lib.png
             └─ ...
          ├─ Library
             └─ ...
          └─ ...

.. raw:: html

    (<a href="_static/lib.png" target="_blank">lib</a>, <a href="_static/favicon.png" target="_blank">favicon</a>)

Then you need to add the background image to the *index.style.scss*

.. code-block:: scss

    @use ...

    body {
        background-image: url("/static/img/lib.png");

        background-repeat: no-repeat;
        background-size: cover;
        background-position: center;

        .main-page-frame {
            background-color: #ffffff44;
        }
    }

*./Library/Assets/src/index.style.scss*

and the favicon image to the *template/base.html*

.. code-block:: html

    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        ...

        <link href="{% static '/img/favicon.png' %}" rel="shortcut icon">

        ...
        {% block scripts %}{% endblock %}
    </head>

*./Library/template/base.html*

Running the app
---------------

Once all files are in place, build the client assets and start the Django
development server:

.. code-block:: sh

    # From the project root in one terminal:
    cd Assets
    npx gulp          # rebuilds bundles on file change

    # And in another terminal:
    python manage.py migrate
    python manage.py runserver

Open ``http://127.0.0.1:8000/`` and log in. The dashboard should render with
the navigation menu, the catalog list should populate, and borrowing a book
should immediately update every other browser window looking at the same
list — that is the live WebSocket sync described in :doc:`sdc_model`.

Cheat sheet
-----------

Naming map::

    controller "catalog"  →  class CatalogController  →  server class Catalog
                          →  tag <catalog>  →  contentUrl /sdc_view/main_app/catalog
    model "Book"          →  registerModel("Book", Book)  →  this.querySet('Book')
    serverCall('borrow', a)  →  server method  def call_borrow(self, channel=None, **a)

Lifecycle order::

    constructor → onInit(...tagAttrs) → onLoad($html) → willShow() → onRefresh()   …   onRemove()

CLI you will use constantly:

.. code-block:: sh

    python manage.py sdc_cc -a <app> -c <controller_snake>   # new controller pair
    python manage.py sdc_new_model -a <app> -m <ModelCamel>  # new SdcModel + form + templates
    python manage.py sdc_make_model_js                       # (re)generate client model classes
    python manage.py sdc_update_url                          # after changing URL patterns
    python manage.py sdc_update_links                        # re-link app Assets/tests/templates

Common gotchas
--------------

- **Models are deny-by-default.** Always override **both** ``is_authorised`` and
  ``get_queryset``, or the model is fully closed.
- **``staff_allowed`` defaults to ``False``** on group-required views — set it
  ``True`` to admit staff.
- **``serverCall`` names match exactly** and may not start with ``_`` or be a
  framework method.
- **Do not register controllers by hand** — ``sdc_cc`` edits the organizer; if you
  move files, rerun ``sdc_update_links`` / fix the organizer import.
- **Use the safe DOM helpers** (``safeRemove()``, ``safeReplace()``,
  ``safeEmpty()``) when tearing down DOM that contains controllers, so their
  ``onRemove`` runs.
- **WebSockets need ASGI.** Run with ``daphne``/``runserver`` (ASGI) — model sync
  (and ``serverCall`` when ``SERVER_CALL_VIA_WEB_SOCKET`` is on) will not work under
  a pure WSGI server.

What to explore next
--------------------

The library app already exercises the central ideas of SDC, but there is much
more available in the runtime. Good next steps are:

- :ref:`sdc-controller-label` — full controller API, event maps, mixins and
  the built-in ``sdc_tools`` controllers.
- :doc:`sdc_model` — advanced queryset usage, relationship serialization, file
  uploads and connection lifecycle.
- :ref:`sdc-how-to-nav` — navigator paths, parametrized navigation, and modal
  subviews.
- :doc:`client` — the bootstrap flow, tag registration and dynamic DOM
  fragments used by the ``borrow_btn`` handler above.

