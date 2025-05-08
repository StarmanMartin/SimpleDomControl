import {AbstractSDC, app} from 'sdc_client';


class UserController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/user"; //<user></user>

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
        this._data = null;
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

    get data() {
        return this._data;
    }

    onInit() {
    }

    onLoad($html) {
        return this.serverCall('get_user').then((user) => {
            const userList = JSON.parse(user);
            if (userList.length > 0) {
                const {fields, pk} = JSON.parse(user)[0];
                this._data = {...fields, pk};
            } else {
                this._data = null;
            }
            return super.onLoad($html);
        });
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {

        return super.onRefresh();
    }

}

app.registerGlobal(UserController);