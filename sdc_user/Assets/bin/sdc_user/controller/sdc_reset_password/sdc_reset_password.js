import {AbstractSDC, app} from 'sdc_client';


/**
 * Sets a new password with a reset token; this is the target of the link in the password-reset e-mail sent by `<sdc-password-forgotten>`.
 *
 * - Arguments: `token` (required) is the token from the e-mail link (`/~sdc-reset-password~&1.token=...`); it is kept in a hidden form field.
 * - Enter the new password twice (at least 8 characters, must match and pass the password rules). No login is needed.
 * - "Reset Password" sets the new password and shows "Password has been reset."; the user is not logged in and must then use `<sdc-login>`.
 * - Each token works once and is valid for 3 days. An expired token automatically sends a new reset e-mail; an invalid or used token shows an error.
 */
class SdcResetPasswordController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_reset_password"; //<sdc-reset-password></sdc-reset-password>

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

app.register(SdcResetPasswordController).addMixin('sdc-auto-submit');