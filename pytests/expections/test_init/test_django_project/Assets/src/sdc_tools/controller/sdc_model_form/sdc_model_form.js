import {AbstractSDC, app, trigger} from "sdc";


export class SdcModelFormController extends AbstractSDC {

    constructor() {
        super();
        this.pk = null;
        this.contentUrl = "/sdc_view/sdc_tools/sdc_model_form"; //<sdc-model-form></sdc-model-form>
        this.model_name = null;

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
    onInit(model, pk, next, filter, on_update, on_error) {
        !this.on_update && (this.on_update = on_update);
        !this.on_error && (this.on_error = on_error);
        !this.next && (this.next = next);
        if(typeof filter === 'function') {
            filter = filter();
        }

        if (this.model_name) {
            model = this.model_name;
        }
        if (typeof (pk) !== "undefined") {
            this.pk = pk;
            this.type = 'edit';
            this.model = this.newModel(model, {pk: pk});
            this.form_generator = this.model.editForm.bind(this.model);
        } else {
            this.isAutoChange = false;
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
        this.from = this.form_generator()
        $html.find('.form-container').append(this.from);
        // $html.find(`.not-${this.type}`).remove();
        return super.onLoad($html);
    }

    onChange() {
        this.from.submit()
    }

    willShow() {
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    submitModelForm($form, e) {
        let self = this;
        return super._submitModelForm($form, e).then(function (res) {
            if (res && res.type === 'create') {
                $form[0].reset();
            }

            self.on_update && self.on_update(res);
        }).catch((res) => {
            self.on_error && self.on_error(res);
        });
    }

    controller_name() {
        return `${this.type.replace(/^./g, letter => letter.toUpperCase())} ${this.model.model_name.replace(/[A-Z]/g, letter => " " + letter).replace(/^./g, letter => letter.toUpperCase())}`
    }

}

app.register(SdcModelFormController).addMixin('sdc-update-on-change');