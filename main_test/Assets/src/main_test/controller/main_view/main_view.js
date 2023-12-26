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
        return <div><button onClick={this.updateHeader}></button><h1 className="test-header">{this.headerText} {args['arg']}</h1></div>
    }

    async_test_view_func(args) {
        return new Promise((resolve)=> {
            setTimeout(()=> {
                resolve(<p className="async-test-header">After 50 mil.sec.</p>);
            }, 50);
        });
    }

    updateHeader(){
        this.headerText = 'Button Pressed!!';
        this.refresh();
    }

}

app.register(MainViewController);