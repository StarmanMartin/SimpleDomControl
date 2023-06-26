import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class UserRegisterController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_user/user_register"; //<user-register></user-register>
        this._cssUrls.push('/static/sdc_user/css/sdc/user_register.css');

        this.contentReload = true;
        this.isAutoChange = false;

        this.events.unshift({

        });
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
        let $picker = this.$container.find("#id_birth_date");

        let picke_data = {
            updateInput: true,
            format: 'd.mm.yyyy',

// Editable input
            editable: false,

// Dropdown selectors
            selectYears: 70,
            selectMonths: true,
            min: $picker.data('date-min'),
            max: $picker.data('date-max')
        };

        let self = this;
        if (!isNaN(this.dayidx)) {
            picke_data.onStart = function () {
                let date = new Date();
                this.set('select', [date.getFullYear(), date.getMonth(), date.getDate() + self.dayidx]);
                self.dayidx = NaN;
            };
        }

        picke_data.onSet = function(context) {

        };

        $picker.pickadate(picke_data);
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

}

app.register(UserRegisterController).addMixin('change-sync-mixin', 'auto-submit-mixin');