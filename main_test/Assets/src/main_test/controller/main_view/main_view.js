import {AbstractSDC, app} from 'sdc_client';


/**
 * Demo page of the framework's test project, used by the Jest tests to exercise controller features; it has no real business purpose.
 *
 * - Requires a logged-in user; anonymous users get a permission-denied (403) error instead of a login redirect.
 * - Shows a list of `<test-item>` children (initially 5) and a test header.
 * - "BB" removes one `<test-item>` from the list and sets the header to "Button Pressed!!"; the two unlabeled buttons only change the header text.
 * - Server calls `call_echo` and `call_async_echo` return their arguments and each create a new `Author` named `XX FF` (age `2`).
 * - Server call `test_echo_call` redirects the browser to `<logged-in>`; `call_no_response` does nothing.
 */
class MainViewController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/main_test/main_view"; //<main-view></main-view>
        this.headerText = "test";
        this.flow_test = ["constructor"];
        this.number = 5;

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
       this.onInit();
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
            <button className="func_view_button" onClick={this.updateHeader.bind(this)}>BB</button>
            <h1 className="test-header">{this.headerText} {args['arg']}</h1></div>
    }

    listview() {
        const listItems = [];
        console.log('listview');
        for (let i = 0; i < this.number; i++) {
            listItems.push(`<test-item data-idx="${i}"></test-item>`);
        }

        return `<div>${listItems.join('\n')}</div>`;
    }

    async_test_view_func() {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(<p className="async-test-header">After 10 mil.sec.</p>);
            }, 10);
        });
    }

    updateHeader() {
        this.number -= 1;
        this.headerText = 'Button Pressed!!';
        this.refresh();
    }

    /**
     * Test button: sets the header text to "attr click". Changes no data.
     */
    attr_sdc_click() {
        this.headerText = 'attr click';
        this.refresh();
    }

}

app.register(MainViewController);