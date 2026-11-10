import {AbstractSDC, app, trigger} from 'sdc_client';


/**
 * Lists, creates and revokes the API tokens of the logged-in user: tokens let programs and AI assistants use the
 * site with the user's account through the REST API (`sdc_api/`) or MCP.
 *
 * - No arguments; login required.
 * - The list shows every token of the user (also expired and revoked ones): name, the first characters of the
 *   token, privileges, creation, expiry and last use. Tokens of `sdc_api/login/` (username and password) are
 *   marked "login".
 * - "Create token" needs a name, a lifetime ("Valid for") and privileges: "Read only" (read all data and the
 *   account), "Read & write" (also create and change data), "Full access" (also delete data, change the profile
 *   and manage tokens) or "Custom" (read/write/delete per data model or for all of them, and the account
 *   privileges). A token never has more rights than the user.
 * - The new token is shown once above the list with a "Copy" button; it cannot be shown again.
 * - "Revoke" asks for confirmation and then revokes the token and every token created with it; this cannot be
 *   undone.
 */
class SdcApiTokensController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_api_tokens"; //<sdc-api-tokens></sdc-api-tokens>
        this.contentReload = true;
        // A plain function, not an arrow function: SDC calls event handlers with the controller instance on the
        // page as `this`, which is not the object this constructor runs on.
        this.events.unshift({'change': {'.token-preset': function () { this._toggleCustom(); }}});
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
        this._toggleCustom();
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    _preset() {
        return this.find('.token-preset:checked').val() || 'read';
    }

    _toggleCustom() {
        this.find('.token-custom').toggleClass('d-none', this._preset() !== 'custom');
    }

    _privileges() {
        const preset = this._preset();
        if (preset !== 'custom') {
            return preset;
        }
        return this.find('.token-privilege:checked').map((_i, el) => el.value).get();
    }

    /**
     * Creates a token with the entered name, lifetime and privileges and shows it once; the list is reloaded.
     */
    create_token() {
        const name = (this.find('.token-name').val() || '').trim();
        if (!name) {
            trigger('pushErrorMsg', 'Upss!', 'Please enter a name for the token.');
            return;
        }
        const privileges = this._privileges();
        if (Array.isArray(privileges) && privileges.length === 0) {
            trigger('pushErrorMsg', 'Upss!', 'Please choose at least one privilege.');
            return;
        }
        const days = this.find('.token-days').val();
        return this.serverCall('create_token', {name, privileges, days}).then((res) => {
            if (!res || !res.token) {
                return;
            }
            return this.reload().then(() => {
                this.find('.new-token-value').val(res.token);
                this.find('.new-token-secret').removeClass('d-none');
                this.find('.token-name').val('');
            });
        });
    }

    /**
     * Copies the new token to the clipboard.
     */
    copy_token() {
        const value = this.find('.new-token-value').val();
        if (navigator.clipboard && value) {
            navigator.clipboard.writeText(value).then(() => trigger('pushMsg', '', 'Copied'));
        } else {
            this.find('.new-token-value').trigger('select');
        }
    }

    /**
     * Revokes the token of the button (`data-token-id`) after a confirmation; tokens created with it are revoked
     * as well.
     */
    revoke_token($btn) {
        const name = $btn.data('token-name');
        if (!window.confirm(`Revoke the token "${name}"? Programs using it lose access at once.`)) {
            return;
        }
        return this.serverCall('revoke_token', {token_id: $btn.data('token-id')}).then(() => this.reload());
    }

}

app.register(SdcApiTokensController, false);
