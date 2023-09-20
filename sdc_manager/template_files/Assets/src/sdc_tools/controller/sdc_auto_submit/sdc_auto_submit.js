import {AbstractSDC, clearErrorsInForm, setErrorsInForm, app} from 'sdc';


export class SdcAutoSubmitController extends AbstractSDC {

    constructor() {
        super();
        //<sdc-auto-submit></sdc-auto-submit>

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncommend the following line to add events;
         */
        this.events.unshift({
            'submit': {
                '.ajax-form': function ($form, ev) {
                    ev.preventDefault();
                    const form = $form[0];
                    this.submitForm(form).then((res) => {
                        if (res.msg || res.header) {
                            app.Global.sdcAlertMessenger.pushMsg(res.header || '', res.msg || '');
                        }
                        clearErrorsInForm($(form));
                        this.onSubmit(res);
                    }).catch((res) => {
                        let data = res.responseJSON;
                        if (data) {
                            if (data.html) {
                                setErrorsInForm($form, $(data.html));
                            }
                            if (data.msg || data.header) {
                                app.Global.sdcAlertMessenger.pushErrorMsg(data.header || '', data.msg || '');
                            }
                        }
                        this.onErrorSubmit(res);
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
    // - onRefresh  (recalled on reload)              //
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

    onRefresh() {
        return super.onRefresh();
    }

    onSubmit() {

    }

    onErrorSubmit() {

    }

    onChange($elem) {
        $elem.closest('.ajax-form').submit();
    }

}

app.register(SdcAutoSubmitController);