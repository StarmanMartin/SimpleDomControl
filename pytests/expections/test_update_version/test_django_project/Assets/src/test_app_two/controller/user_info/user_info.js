import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class UserInfoController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/user_info"; //<user-info></user-info>
		// _cssUrls is deprecated and will be ignored in the new version!
        this._cssUrls.push('/static/sdc_user/css/sdc/user_info.css');

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

		// afterShow is deprecated and will be ignored in the new version!
 		// If you use afterShow you can call the function in onRefresh
    afterShow() {
		// super.afterShow is not available anymore in the new version!
 		//        return super.afterShow();
    }

    onRefresh() {
		this.afterShow();
        return super.onRefresh();
    }

}

app.register(UserInfoController);