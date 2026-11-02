import {AbstractSDC, app} from 'sdc_client';


/**
 * Test fixture of the framework's test project; it shows only the static test heading "Error404".
 *
 * Despite its name it is not an error handler: it is open to everyone and shows and changes no data.
 */
class Error404Controller extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/error_404"; //<error404></error404>

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
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(Error404Controller);