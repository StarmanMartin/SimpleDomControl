import {AbstractSDC, app} from 'sdc_client';


class TestSdcOneController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/test_app_one/test_sdc_one"; //<test-sdc-one></test-sdc-one>
        // this.contentReload = true; // reload the HTML for every instance (no cache)
        // this.load_async = true; // the parent does not wait for this controller
        // DOM events (plain functions, this = controller):
        // this.events.unshift({click: {'.selector': function ($elem, ev) {}}});
    }

    // Lifecycle: onLoad($html) before the DOM is set, willShow() after, onRefresh() on reload, onRemove()

    onLoad($html) {
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(TestSdcOneController, false);