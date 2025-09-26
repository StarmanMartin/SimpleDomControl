First App
=========

We want to create a library app.
A library has books that can be borrowed online. However, each book can only be borrowed once.

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


.. include:: basic_navigation.rst

see more: :ref:`sdc-how-to-nav`


DB Model
--------

Now that navigation through the available pages has been implemented, the next step is to fill the pages with content. To do this,
 First, we need to create a new database table. For this, we will use an extension of the Django ORM (Object-Relational Mapper).
In SDC, these model classes do not need to be created manually. This can be done with a simple SDC command.

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

.. code-block:: python

    ...
    class Book(models.Model, SdcModel):
        title = models.CharField(max_length=100)
        author = models.CharField(max_length=100)
        text = models.CharField(max_length=255, default=default_text)
        borrowed_by = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

        class SearchForm(AbstractSearchForm):
            """A default search form used in the list view. You can delete it if you dont need it"""
            CHOICES = (("title", "Title"), ("author", "Author"),)
            PLACEHOLDER = "Title or Author"
            DEFAULT_CHOICES = CHOICES[0][0]
            SEARCH_FIELDS = ("title", "author")

        class _SdcMeta:
            """Meta data information needed to manage all SDC operations."""
            edit_form = "main_app.forms.BookForm"
            create_form = "main_app.forms.BookForm"
            html_list_template = "main_app/models/Book/Book_list.html"
            html_detail_template = "main_app/models/Book/Book_details.html"

        @classmethod
        def render(cls, template_name, context=None, request=None, using=None):
            if template_name == cls.SdcMeta.html_list_template:
                sf = cls.SearchForm(data=context.get("filter", {}))
                context = context | handle_search_form(context["instances"], sf, range=3)
            return render_to_string(template_name=template_name, context=context, request=request, using=using)

        @classmethod
        def is_authorised(cls, user, action, obj):
                return True

        @classmethod
        def get_queryset(cls, user, action, obj):
            return cls.objects.all()


*./Library/main_app/models.py*

In SDC, the model is responsible for managing its own access rights. To ensure secure authorisation, edit the 'is_authorised' method.

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
                case _: # edit_form, named_form, create_form, list_view, detail_view, save, create, upload, delete, load
                    return False
    ...

*./Library/main_app/models.py*

Since we do not need the forms for the books, this object can be ignored in this case. First, we should take care of the representation in the client.

Client-Side Data Models
-----------------------

The user should be able to browse the books as a list and view a detailed view of the individual books. SDC offers a ListView and a DetailView for the client for this purpose.


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




