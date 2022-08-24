import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class GAlertMsgController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/g_alert_msg"; //<g-alert-msg></g-alert-msg>
        this._cssUrls.push('/static/sdc_tools/css/sdc/g_alert_msg.css');
        this.msg_counter = 0;
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

    push_msg(header, msg) {
        return this._push_msg(header, msg, false);
    }

    push_error_msg(header, msg) {
        return this._push_msg(header, msg, true);
    }

    _push_msg(header, msgList, isError) {
        if (typeof msgList === 'string') {
            msgList = [msgList];
        }

        for (let msg of msgList) {
            this._push_msg_array(header, msgList, isError);
        }
    }

    _push_msg_array(header, msg, isError) {
        let $dummyRow = this.find('.dummy_row');
        let $cloneRow = $dummyRow.clone();
        $cloneRow.removeClass('dummy_row');
        if (isError) {
            $cloneRow.addClass('error_box');
        }

        $cloneRow.find('.msg_header').text(header);
        $cloneRow.find('.msg_body').text(msg);
        let nowDate = new Date();

        let minutes = nowDate.getMinutes();
        minutes = minutes < 10 ? '0' + minutes : minutes;

        $cloneRow.find('.msg_date').text(nowDate.getHours() + ':' + minutes);
        $cloneRow.insertAfter($dummyRow);
        let self = this;
        this.msg_counter++;
        this.find('.alert_msg_container').addClass('active');
        (function ($delRow) {
            setTimeout(() => {
                $delRow.remove();
                self.msg_counter--;
                if (self.msg_counter === 0) {
                    self.find('.alert_msg_container').removeClass('active');
                }
            }, 2000);
        })($cloneRow);
    }

}

app.registerGlobal(GAlertMsgController);