import {AbstractSDC, app} from 'sdc_client';


/**
 * Error page that shows "We have an error: <code>" for the HTTP status in its `code` argument.
 *
 * - `<sdc-navigator>` shows `sdc-error 404` when a path segment names an unknown controller.
 * - `sdc-error 403` (or similar) means the server refused the view: log in, or use a user with the required permissions.
 * - It has no actions; navigate elsewhere (link, breadcrumb, browser back) to leave it.
 */
export class SdcErrorController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/sdc_error/%(code)s"; //<sdc-error data-code=""></sdc-error>

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncommend the following line to add events;
         */
        // this.events.unshift({'click': {'.header-sample': (ev, $elem)=> $elem.css('border', '2px solid black')}}});
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
        $html.find('.error_content').append(this.$container.html());
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(SdcErrorController);