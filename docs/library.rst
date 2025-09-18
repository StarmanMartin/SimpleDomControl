First App
=========

We want to create a library app.
A library has books that can be borrowed online. However, each book can only be borrowed once.

First we need to create a new project. First cd into the development directory.

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


Add a background images to the static directory:

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

edit the *index.style.scss*

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


Add a catalog controller and a my_list controller:

.. code-block:: sh

    python manage.py sdc_cc -a main_app -c catalog
    python manage.py sdc_cc -a main_app -c my_list
