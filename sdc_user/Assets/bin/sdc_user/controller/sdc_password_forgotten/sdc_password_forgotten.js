import {AbstractSDC, app} from 'sdc_client';


/**
 * Requests a password-reset e-mail for a user who forgot their password; reached from the "Password forgotten" link of `<sdc-login>`.
 *
 * - No arguments and no login needed. Enter the username or the e-mail address of the account.
 * - "Send E-mail" sends an e-mail with a link to `<sdc-reset-password>` to the account's address; the link is valid for 3 days and can be used once.
 * - Shows "User not found" if no account (or more than one) matches, and an error if the e-mail could not be sent.
 */
class SdcPasswordForgottenController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_password_forgotten"; //<sdc-password-forgotten></sdc-password-forgotten>

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

    send_email() {
        const mail = this.find('#id_username').val();
        this.serverCall('send_email', {mail})

    }

}

app.register(SdcPasswordForgottenController);