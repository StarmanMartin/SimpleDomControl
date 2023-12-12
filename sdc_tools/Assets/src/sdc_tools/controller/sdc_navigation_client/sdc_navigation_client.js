import {AbstractSDC, app, trigger, on} from 'sdc_client';

export class SdcNavigationClientController extends AbstractSDC {

    constructor() {
        super();
        //<sdc-navigation-client></sdc-navigation-client>
        this.menu_id = 0;

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
        on('_onResize', this);
        return super.onLoad($html);
    }

    willShow() {
        trigger('navLoaded', this);
        trigger('changeMenu', this.menu_id);
        return super.willShow();
    }

    _onResize() {
        this.onResize();
    }

    onResize() {

    }

}

app.register(SdcNavigationClientController);