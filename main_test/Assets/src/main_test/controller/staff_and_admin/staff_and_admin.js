import {AbstractSDC, app} from 'sdc_client';


/**
 * Test fixture of the framework's test project for the group/staff access check; it shows only a static test heading.
 *
 * - May be opened by logged-in staff users and superusers; no group grants access.
 * - Anyone else (anonymous or without permission) is redirected to `<sdc-login>`, with `next` pointing back to the parent view.
 * - Shows and changes no data.
 */
class StaffAndAdminController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/staff_and_admin"; //<staff-and-admin></staff-and-admin>

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

app.register(StaffAndAdminController);