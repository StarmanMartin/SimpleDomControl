---
name: sdc-ai-knowledge
description: Documenting a SimpleDomControl (SDC) project for its AI assistant and MCP clients — use when writing model docstrings, controller JSDoc or button-action comments, when sdc_prepare_teaching reports undocumented items, or when running sdc_teach.
---

# Knowledge for the AI assistant (`sdc_teach`)

The AI assistant (`<sdc-ai-assistant>`) and MCP clients learn the project from the documentation in the code.

```
python manage.py sdc_prepare_teaching       # guide + list of undocumented models, controllers, button actions
python manage.py sdc_teach --per-app --no-ask   # writes <app>/SDC_SKILL.json from the code (no browser needed)
```

`sdc_prepare_teaching` prints the full writing guide; its list at the end must be empty.

## Where the documentation goes

- **Model**: the class docstring.
  ```python
  class Book(models.Model, SdcModel):
      """A book with a `title`, written by one `Author`.

      - Logged-in users may read all books; only staff may create, change or delete them.
      - Deleted automatically when its author is deleted.
      """
  ```
- **Controller**: a JSDoc block directly above the class in the controller JS file.
  ```js
  /**
   * Lists the titles of all books; each title opens <book-detail>.
   *
   * - No arguments. "Count books" shows the number of books.
   */
  class BookListController extends AbstractSDC {
  ```
- **Button action**: a JSDoc block directly above the method a button calls (`sdc_click="remove"` →
  `remove($btn) {`): what happens for the user, whether data is changed or deleted, whether it can be undone.
- `@ai-hidden` in a controller's JSDoc hides it from the assistant (frames, mixins).

Write for a user of the app, not for a developer: what it shows, which arguments it takes, what the buttons do,
who may do what.
