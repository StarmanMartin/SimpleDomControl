First App
=========

Wir wollen eine Bücherrei app erstellen.
Eine Bücherrei hat Bücherei hat bücher und

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

.. code-block:: sh

    python manage.py startapp main_app

Add main_app to basic

.. code-block:: python

    ...
    INSTALLED_APPS = ['daphne'] + INSTALLED_APPS + ['channels', 'sdc_tools', 'sdc_user', 'main_app']
    ...

*./Library/Library/settings.py*

.. code-block:: sh

    python manage.py migrate
    python manage.py createsuperuser


.. code-block:: sh

    python manage.py sdc_cc

Output:

.. code-block:: sh

    Enter number to select an django App:
    1 -> main_app
    Enter number: [1] 1
    Enter the name of the new controller (use snake_case): dashboard

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
