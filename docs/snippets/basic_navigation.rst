
SDC links need to have the ``navigation-links`` class. Links with this class are
handled by the SDC navigation controller. The navigation system allows dynamic
navigation based on an easy-to-learn syntax. The following are examples of the
``href`` attribute used by navigation links.

- ``/view-a/view-b`` -> ``view-b`` as subview of ``view-a``
- ``*/view-b`` -> keeps the first view as it is and renders ``view-b`` as subview
- ``../view-b`` -> replaces the current deepest subview with ``view-b``
- ``./view-b`` -> adds ``view-b`` as the next subview in the current path

The first path element in ``href`` always represents the **main view**, which
is displayed in the root navigation area.

Each additional path element is displayed inside a ``<div>`` with the class
``sdc_detail_view``.

When the controller defined in the fifth path element is loaded, it checks
whether the view from the fourth path element already contains an element with
the ``sdc_detail_view`` class.

- If it does, the fifth view is placed inside that ``sdc_detail_view`` container.
- If it does not, the fifth view replaces the fourth view entirely.
