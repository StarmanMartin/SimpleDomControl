.. _sdc-controller-label:

SDC controller
==============

A controller has two parts a client and a server. This is preceded by a short chapter on generating a controller.
This is followed by a paragraph on how the
server code is to be understood. This is followed by a short
overview of the client code (HTML, SCSS, JavaScript)

.. _new-controller-controller:

New controller
--------------

We recommend delegating the creation of controllers to the provided scripts designed for this purpose.
To initiate the creation of a new controller, execute the following command within the project directory:

.. code-block:: sh

    $ python manage.py sdc_cc

To complete the process, you will be prompted with two questions in the terminal. Firstly,
specify the Django app in which the controller should be created (for example, *mypage*).
Secondly, provide a name for the new controller (in this example, the name is about_me).
It's important to note that only snake case should be used for the controller name. For additional details, refer to :ref:`sdc-cc-core`.

Alternative können die fragen auch übergangen werden.


.. code-block:: sh

    $ python manage.py sdc_cc -a <django_app_name> -c <sdc_controller_name>

Jedoch muss der *sdc_controller_name* im **snake_case** angegeben werden. Wenn die django app nich in den
settings angegeben ist wir der angegeben parameter ignoriert.



Auch wenn die die Model objecte die server logig zum großen teil ünerehemen kann gib SDC die möglichkeit



