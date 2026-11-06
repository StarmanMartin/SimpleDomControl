import {AbstractSDC, app} from 'sdc_client';


/**
 * Registration form that creates a new `SdcUser` account; open it from the "Register" link of `<sdc-login>` or `<sdc-user-nav-btn>`.
 *
 * - Arguments: `model` must be `SdcUser`; `next` is where to go after creating (the links pass `..`, i.e. back).
 * - Fields: `username`, `first_name`, `last_name`, `email`, the password and its confirmation (must match and pass the password rules).
 * - "Create" creates the account; anyone may register, no login is needed. The new user is not logged in automatically.
 * - If an `email` was given, a confirmation e-mail with a link to `<sdc-confirm-email>` (valid 3 days) is sent to it.
 * - If the project requires confirmed e-mail addresses, the new user can only log in after following that link.
 *
 * @ai-task Register a new account
 * 1. Open `/~register~&model=SdcUser&next=..` (or the "Register" link).
 * 2. Fill `username`, `password1` and `password2` (the user types the passwords) and optionally the names and `email`.
 * 3. The user clicks "Create"; with an `email` a confirmation e-mail is sent.
 */
class RegisterController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/register"; //<register></register>
        this.model_name = "SdcUser";

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

app.register(RegisterController, false).addMixin('sdc-model-form');