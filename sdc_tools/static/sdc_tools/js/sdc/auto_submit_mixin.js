import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class AutoSubmitMixinController extends AbstractSDC {

    constructor() {
        super();
        //<auto-submit-mixin></auto-submit-mixin>
        this._cssUrls.push('/static/sdc_tools/css/sdc/auto_submit_mixin.css');
        this.events.unshift({
            '.ajax-form': {
                'submit': function(form, ev) {
                    ev.preventDefault();
                    this.submitForm(form).then((res)=> {
                        if (res.msg || res.header) {
                            app.Global.gAlertMsg.push_msg(res.header || '', res.msg || '');
                        }

                       this.onSubmit(res);
                    }).catch((res)=> {
                        let data = res.responseJSON;
                        if(data) {
                            if (data.html) {
                                this.setErrorsInForm($(form), $(data.html).find('.ajax-form'));
                            }
                            if (data.msg || data.header) {
                                app.Global.gAlertMsg.push_error_msg(data.header || '', data.msg || '');
                            }
                        }
                    });
                }
            }
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
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    onSubmit() {

    }

}

app.register(AutoSubmitMixinController);