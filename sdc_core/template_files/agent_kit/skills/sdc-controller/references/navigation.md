# SDC navigation and URLs

The app is a single page: the `sdc-navigator` shows nested views (SDC controllers) and the URL lists them.

- `/~parent-view~child-view~&key=value&other=2`: one controller tag per `~` segment, outermost first; every view is rendered inside the previous one. The part before the first `~` (usually `/`) is the Django page.
- The arguments start at the first `&` (or `?`): `key=value` pairs joined by `&`. Values are URL-decoded; numbers and `true`/`false` become numbers and booleans.
- A plain key belongs to the deepest view of the path. `N.key` belongs to the view at depth `N` (1 = first view): `/~book-list~book-edit~&1.page=2&pk=3` gives `page=2` to `book-list` and `pk=3` to `book-edit`. A view receives its arguments as `this.params` (`data-*` attributes; `camelCase` keys become `kebab-case`). The links of the current URL show the arguments with their depth (`2.pk=3`).
- Navigating keeps the arguments of the views above the opened view; the opened view gets only the arguments given.
- Relative paths are resolved against the current URL: `.` = the current path, `..` = one view up, `*` = keep the view at this depth, `..~other-view` replaces the deepest view, `.~child-view~&pk=3` opens a view below the current one. A path that does not start with `/`, `~`, `.` or `*` also opens below the current view (`book-edit` = `.~book-edit`).
- An empty path (`/`) opens the navigator's default controller; a view may open a default child view by itself.
- An unknown tag shows `sdc-error 404`; a view the user may not open shows `sdc-error 403`.
- `window.sdcNav.goTo(path, {key: value})`, the `goTo` event and links with the class `navigation-links` navigate without reloading the page (the AI assistant's `navigate` and `click` do the same). Opening the URL directly loads the whole page.

## Links and navigation in code

- Template link to a view: `<a class="navigation-links" href="/~book-detail~&pk={{ book.pk }}">{{ book.title }}</a>`
  (the class makes it navigate without a page reload).
- In a controller: `window.sdcNav.goTo('/~book-detail', {pk: 3})`.
- The arguments arrive in the opened controller as `onInit(...)` parameters and `this.params`.
- A view may only be allowed below certain views: `this.allowedPaths = [['**', 'dashboard']]` in the client
  controller (patterns of the views in front of it; `[]` = anywhere).
