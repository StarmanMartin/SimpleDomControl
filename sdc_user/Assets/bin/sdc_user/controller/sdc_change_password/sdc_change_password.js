import {AbstractSDC, app} from 'sdc_client';


/**
 * Form for the logged-in user to change their own password (the `password_form` of `SdcUser`).
 *
 * - No arguments; it always edits the current user. Requires login, otherwise it redirects to the login view.
 * - Enter the current password, then the new password twice (must match and pass the password rules).
 * - "Change password" saves the new password immediately. Other sessions of this user are logged out; the current session stays logged in.
 */
class SdcChangePasswordController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_change_password"; //<sdc-change-password></sdc-change-password>

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
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(SdcChangePasswordController);