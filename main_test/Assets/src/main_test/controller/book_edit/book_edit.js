import {AbstractSDC, app} from 'sdc_client';


/**
 * Demo form for one `Book`, used by the framework's tests; it reuses the `<sdc-model-form>` behaviour.
 *
 * - Arguments: `pk` (or `id`) is the id of the book to edit; without it the form creates a new `Book`.
 * - In edit mode every field change is saved immediately via the model socket; there is no separate save button.
 * - "Add X to name" appends ` X` to the title and sets `author` to the author with id `1`, in the form's model object only (not saved by this button itself).
 * - Open to everyone, no login required.
 */
class BookEditController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/book_edit"; //<book-edit></book-edit>

        /**
         * Uncomment the following line to make sure the HTML template
         * of this controller is not cached and reloaded for every instance
         * of this controller.
         */
        // this.contentReload = true;

        /**
         * Uncomment the following line to make this controller asynchronous.
         * This means that the parent controller finishes loading without
         * waiting for this controller
         */
        // this.load_async = true;

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncomment the following line to add events;
         */
        // this.events.unshift({'click': {'.header-sample': (ev, $elem)=> $elem.css('border', '2px solid black')}});
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - onRefresh  (recalled on reload)              //
    //-------------------------------------------------//
    // - onRemove                                      //
    //-------------------------------------------------//

    onLoad($html) {
      this.model_name = 'Book';
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    add_x() {
      this.model.title ??= ' -> ';
      this.model.title += ' X';
      this.model.author = 1;
    }

}

app.register(BookEditController, false).addMixin("sdc-model-form");