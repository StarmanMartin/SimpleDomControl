import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {trigger} from "../../../simpleDomControl/sdc_events";


class SdcModelFormController extends AbstractSDC {

    constructor() {
        super();
        this.pk = null;
        this.contentUrl = "/sdc_view/sdc_tools/sdc_model_form"; //<sdc-model-form></sdc-model-form>

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
    onInit(model, pk, next, filter, on_update ) {
        this.on_update = on_update;
        if(typeof filter === 'function') {
            filter = filter();
        }

        if (this.model_name) {
            model = this.model_name;
        }
        this.next = next;
        if (typeof (pk) !== "undefined") {
            this.pk = pk;
            this.type = 'edit';
            this.model = this.newModel(model, {pk: pk});
            this.form_generator = this.model.editForm.bind(this.model);
        } else {
            this.type = 'create';
            this.model = this.newModel(model);
            this.form_generator = this.model.createForm.bind(this.model);
        }
        if(typeof filter === 'object') {
            this.model.filter(filter);
        }
    }

    onLoad($html) {
        this.model.on_update = () => {
            if (this.next) {
                trigger('onNavigateToController', this.next);
            }
        }
        const from = this.form_generator()
        $html.find('.form-container').append(from);
        // $html.find(`.not-${this.type}`).remove();
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    submitModelForm($form, e) {
        return super.submitModelForm($form, e).then(function (res) {
            if (res && res.type === 'create') {
                $form[0].reset();
            }

            this.on_update && this.on_update(res);
        }).catch(() => {
        });
    }

}

app.register(SdcModelFormController);