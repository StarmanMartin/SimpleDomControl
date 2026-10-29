import {AbstractSDC, app} from 'sdc_client';


/**
 * Test fixture of the framework's test project for the group/staff access check; it shows only a static test heading.
 *
 * - Only logged-in superusers may open it; staff status or group membership is not enough.
 * - Anyone else (anonymous or without permission) is redirected to `<sdc-login>`, with `next` pointing back to the parent view.
 * - The Jest tests also use it as an empty host controller for `SdcModel` tests; it changes no data itself.
 */
class AdminOnlyController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/admin_only"; //<admin-only></admin-only>

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncomment the following line to add events;
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

app.register(AdminOnlyController);