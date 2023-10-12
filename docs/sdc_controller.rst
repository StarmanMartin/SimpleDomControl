.. _sdc-controller-label:
SDC controller
=============

A controller has two parts a client and a server.Vorab folgt
ein klenes Kapitel über das generieren eines Controllers.
Darauf folgend wir in einem absätzen vorgestellt wie der
Server code zu verstehen ist. Darauf volgent kommt ein kurzer
überplick über den Client code (HTML, SCSS, JavaScript)

.. _new-controller-label:
New controller
-------------

Wir bitten sie das Erstellen von Contollern dem dafür bereit gestellen
script zu überlassen. Um einen neuen controller zu erwtellen führen
sie follgenden Befehl in dem Prpjekt Verzeichniss aus.

.. code-block:: sh

    $ python manage.py sdc_cc

You will need two answer two questions in the terminal to finish the process.
Firstly, it needs to know in witch Django app (we choose  *mypage* in the example below)
the controller has to be created. Secondly, you have to give the new controller a name
(in the example the name is *about_me*). Importante, only use snake case for the controller
name. See  for more details.

Alternative können die fragen auch übergangen werden.


.. code-block:: sh

    $ python manage.py sdc_cc -a <django_app_name> -c <sdc_controller_name>

Jedoch muss der *sdc_controller_name* im **snake_case** angegeben werden. Wenn die django app nich in den
settings angegeben ist wir der angegeben parameter ignoriert.



Auch wenn die die Model objecte die server logig zum großen teil ünerehemen kann gib SDC die möglichkeit



