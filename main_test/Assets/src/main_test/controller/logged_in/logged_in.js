import {AbstractSDC, app} from 'sdc_client';


/**
 * Test fixture of the framework's test project; it shows only the static test heading "LoggedIn".
 *
 * - Open to everyone; despite its name it does not require a login.
 * - Target of the `test_echo_call` server call of `<main-view>`, which redirects the browser to `/logged-in`.
 * - Shows and changes no data.
 */
class LoggedInController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/logged_in"; //<logged-in></logged-in>

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

app.register(LoggedInController);