import {AbstractSDC, app} from 'sdc_client';


class MainViewController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/main_view"; //<main-view></main-view>
        this.headerText = "test";
        this.flow_test = ["constructor"];

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncommend the following line to add events;
         */
        this.events.unshift({
            'click': {
                '.class_sdc_click': function () {
                    this.headerText = "Class click";
                    this.refresh();
                }
            }
        });
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
        this.flow_test.push('onInit');
    }

    onLoad($html) {
        this.flow_test.push('onLoad');
        return super.onLoad($html);
    }

    willShow() {
        this.flow_test.push('willShow');
        return super.willShow();
    }

    onRefresh() {
        this.flow_test.push('onRefresh');
        return super.onRefresh();
    }

    test_view_func(args) {
        return <div>
            <button className="func_view_button" onClick={this.updateHeader.bind(this)}></button>
            <h1 className="test-header">{this.headerText} {args['arg']}</h1></div>
    }

    async_test_view_func() {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(<p className="async-test-header">After 10 mil.sec.</p>);
            }, 10);
        });
    }

    updateHeader() {
        this.headerText = 'Button Pressed!!';
        this.refresh();
    }

    attr_sdc_click() {
        this.headerText = 'attr click';
        this.refresh();
    }

}

app.register(MainViewController);