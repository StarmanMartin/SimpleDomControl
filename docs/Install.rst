Installation
============

Requirements
------------

To use SDC comfortably you should have:

- Python 3.10 or newer
- Django 4.2 or newer
- Node.js 18 or newer
- npm or yarn for the client asset/runtime package

Install the Python package
--------------------------

Install the backend package from PyPI:

.. code-block:: sh

   pip install simpledomcontrol

The package is also available from the project releases on GitHub, but PyPI is
the normal installation path for application development.

What gets installed
-------------------

The Python installation gives you the Django integration:

- ``sdc_core``
- management commands
- websocket and model integration helpers
- templates and initialization tooling

The JavaScript runtime used by generated projects is handled in the project
itself through ``npm install`` or ``yarn install`` after ``sdc_init`` has added
the client asset setup.

Next step
---------

Continue with :doc:`getting_started` to initialize a project and install the
client runtime files.
