import {AbstractSDC, app} from 'sdc_client';


/**
 * Confirms the e-mail address of an `SdcUser`; this is the target of the link in the confirmation e-mail.
 *
 * - Arguments: `token` (required) is the token from the e-mail link (`/~sdc-confirm-email~&1.token=...`).
 * - Opening the view with a valid token immediately marks the address as confirmed (`email_confirmed`) and shows a success message; there is nothing to click. No login is needed.
 * - Each token works once and is valid for 3 days. An expired token automatically sends a new confirmation e-mail; an invalid or already used token shows "No valid token.".
 */
class SdcConfirmEmailController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_confirm_email/%(token)s"; //<sdc-confirm-email data-token=""></sdc-confirm-email>

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

app.register(SdcConfirmEmailController);