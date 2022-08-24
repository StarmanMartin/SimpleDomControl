import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class ListMixinController extends AbstractSDC {

    constructor() {
        super();
        //<list-mixin></list-mixin>
        this._cssUrls.push('/static/sdc_tools/css/sdc/list_mixin.css');
        this.events.unshift({});
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - afterShow  (recalled on reload)               //
    //-------------------------------------------------//
    // - onRefresh                                     //
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

    afterShow() {
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }


    update() {
        let $form = this.$container.find('.search-form');
        let self = this;
        if ($form && $form.length > 0) {
            $form.each(function () {
                self.onSearch(this.id);
            });
        }
    }

    onSearch(form) {
        return this.submitForm(form).then((res)=> {
            app.safeReplace(this.find('.list-container'), $(`<div>${res}</div>`).find('.list-container'));
            app.safeReplace(this.find('.search-view-container'), $(`<div>${res}</div>`).find('.search-view-container'));
        });
    };

}

app.register(ListMixinController);