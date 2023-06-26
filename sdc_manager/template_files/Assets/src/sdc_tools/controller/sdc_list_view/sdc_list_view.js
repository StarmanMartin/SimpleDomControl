import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class SdcListViewController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/sdc_list_view"; //<sdc-list-view></sdc-list-view>
        this.search_values = {};

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

    onInit(model) {
        this.model = this.newModel(model);
    }

    onLoad($html) {
        $html.filter('.list-container').append(this.model.listView(this.search_values));
        this.model.on_update = this.model.on_create = ()=> {
            this._updateView()
        };
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    removeInstance($btn, e) {
        this.model.delete($btn.data('instance-pk'));
    }

    onSearch(form) {
        const formData = new FormData(form);
        formData.forEach((value, key) => this.search_values[key] = value);
        this._updateView();
    }

    _updateView() {
        this.find('.list-container').safeEmpty().append(this.model.listView(this.search_values));
    }
}

app.register(SdcListViewController);