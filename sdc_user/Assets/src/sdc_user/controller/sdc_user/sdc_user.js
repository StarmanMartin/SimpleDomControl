import {AbstractSDC, app} from 'sdc_client';


class SdcUserController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/sdc_user"; //<sdc-user></sdc-user>
        this.user = null;

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
        return this.serverCall('get_user_id').then((user_id) => {
            if (user_id !== null) {
                this.user = this.newModel('SdcUser', {'id': user_id});
                return this.user.load().then(() => {
                    return super.onLoad($html);
                });
            }
        });
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(SdcUserController);