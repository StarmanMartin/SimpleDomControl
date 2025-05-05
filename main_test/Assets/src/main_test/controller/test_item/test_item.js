import {AbstractSDC, app} from 'sdc_client';


class TestItemController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/test_item"; //<test-item></test-item>

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

    onInit(idx) {
        console.log(idx);
        this.idx = idx;
    }

    onLoad($html) {
        $html.append(`<input sdc_change="on_change" name="i_${this.idx}" />`);
        return super.onLoad($html);
    }

    on_change() {
        alert(this.idx);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(TestItemController);