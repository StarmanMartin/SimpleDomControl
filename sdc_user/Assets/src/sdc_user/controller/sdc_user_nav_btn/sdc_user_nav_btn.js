import {AbstractSDC, app, on} from 'sdc_client';


/**
 * User area for the navigation bar: shows "Login" and "Register" links when nobody is logged in, and an "Edit <username>" link (opens the user's own `SdcUser` in `<sdc-model-form>`) an "API tokens" link (opens `<sdc-api-tokens>`) and `<sdc-logout>` when a user is logged in. It refreshes itself after login and logout.
 */
class SdcUserNavBtnController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_user_nav_btn"; //<sdc-user-nav-btn></sdc-user-nav-btn>

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
        on('login', this);
        on('logout', this);
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    login() {
        this.reload();
    }

    logout() {
        this.reload();
    }

}

app.register(SdcUserNavBtnController);