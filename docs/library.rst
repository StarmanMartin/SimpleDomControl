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


.. include:: snippets/basic_navigation.rst

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

.. include:: snippets/book_model.rst

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
                case 'load':
                    return True
                case _: # edit_form, named_form, create_form, list_view, detail_view, save, create, upload, delete, load
                    return False
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

*./Library/Assets/src/main_app/models/Books/Books_list.html*

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

*./Library/Assets/src/main_app/models/Books/Books_details.html*



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




