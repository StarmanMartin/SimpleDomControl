import {AbstractSDC, app, trigger, socketReconnect} from 'sdc';

class SdcLogoutController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_logout"; //<sdc-logout></sdc-logout>

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncommend the following line to add events;
         */
        // this.events.unshift({'click': {'.header-sample': (ev, $elem)=> $elem.css('border', '2px solid black')}}});
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - onRefresh  (recalled on reload)              //
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

    onRefresh() {
        return super.onRefresh();
    }

    onSubmit() {
        socketReconnect();
        trigger('logout');
    }

}

app.register(SdcLogoutController).addMixin('sdc-auto-submit');