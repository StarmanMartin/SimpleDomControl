
SDC links need to have the 'navigation-links' class. Links with this class are handled by the SDC-Navigation controller.
The underlying navigation allows dynamic navigation based on a easy to learn syntax. The following are some examples of the 'href' attribute of navigation links.

- /view-a/view-b -> view-b as subview of view-a
- \*/view-b -> keeps first view as it is and view-b as subview
- ../view-b -> replaces current latest subview by view-b
- ./view-b -> adds view-b as next latest subview to the current path

The first part of the *href* path always represents the **main view**, which is displayed in the root navigation area.

Each additional path element is displayed inside a <div> with the class *sdc_detail_view*.

When the controller defined in the 5th path element is loaded, it checks whether the view from the 4th path element already contains an element with the +sdc_detail_view* class.

- If it does, the 5th view will be placed inside that *sdc_detail_view* container.
- If it does not, the 5th view will replace the 4th view entirely.