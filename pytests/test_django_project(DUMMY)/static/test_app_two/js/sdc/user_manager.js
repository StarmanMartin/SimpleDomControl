import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class UserManagerController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/user_manager"; //<user-manager></user-manager>
        this._cssUrls.push('/static/sdc_user/css/sdc/user_manager.css');

        this.contentReload = true;

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
        this.find('.navigation-links').addClass('dropdown-item');
        return super.afterShow();
    }

    onRefresh() {
        this.find('.navigation-links').addClass('dropdown-item');
        return super.onRefresh();
    }

}

app.register(UserManagerController);