import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {trigger} from "../../../simpleDomControl/sdc_events.js";


class NavClientController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/nav_client"; //<nav-client></nav-client>
        this._cssUrls.push('/static/sdc_tools/css/sdc/nav_client.css');
        this.menu_id = 0;
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
    // - onRemove                                      //
    //-------------------------------------------------//

    onInit() {
    }

    onLoad($html) {
        return super.onLoad($html);
    }

    willShow() {
        trigger('navLoaded');
        trigger('changeMenu', this.menu_id);
        return super.willShow();
    }

    afterShow() {
        return super.afterShow();
    }

}

app.register(NavClientController);