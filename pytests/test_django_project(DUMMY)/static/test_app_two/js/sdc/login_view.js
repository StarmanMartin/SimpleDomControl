import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {trigger} from "../../../simpleDomControl/sdc_events.js";
import {log_test} from './utils/sample_utils.js';
import {log_test_outer} from '../utils_outer/sample_utils.js';
import {cake} from './user_confirm_email.js'
import _ from 'lodash'
import 'jquery'

class LoginViewController extends AbstractSDC {

    constructor() {
        super();
        _
        console.log(cake);
        log_test();
        log_test_outer()
        this.contentUrl = "/sdc_view/sdc_user/login_view"; //<login-view></login-view>
        this._cssUrls.push('/static/sdc_user/css/sdc/login_view.css');

        this.contentReload = true;
        this.isAutoChange = false;

        this.events.unshift({

        });
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - afterShow  (recalled on reload)               //
    //-------------------------------------------------//
    // - onRefresh                                     //
    //-------------------------------------------------//
    // - onRemove                                      //
    //-------------------------------------------------//

    onInit() {
    }

    onLoad($html) {
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    afterShow() {
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    onSubmit(res) {
        trigger('login', res.pk)
    }

}

app.register(LoginViewController).addMixin('change-sync-mixin', 'auto-submit-mixin');