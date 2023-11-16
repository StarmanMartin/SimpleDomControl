import {AbstractSDC, app} from 'sdc';


export class SdcAlertMessengerController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/sdc_alert_messenger"; //<sdc-alert-messenger></sdc-alert-messenger>
        this.msgCounter = 0;

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

    pushMsg(header, msg) {
        return this._pushMsg(header, msg, false);
    }

    pushErrorMsg(header, msg) {
        return this._pushMsg(header, msg, true);
    }

    _pushMsg(header, msgList, isError) {
        if (typeof msgList === 'string') {
            msgList = [msgList];
        }

        for (let msg of msgList) {
            this._pushMsgArray(header, msgList, isError);
        }
    }

    _pushMsgArray(header, msg, isError) {
        let $dummyRow = this.find('.dummy_row');
        let $cloneRow = $dummyRow.clone();
        $cloneRow.removeClass('dummy_row');
        if (isError) {
            $cloneRow.addClass('error_box');
        }

        $cloneRow.find('.msg_header').text(header);
        $cloneRow.find('.msg_body')[0].innerHTML = msg;
        let nowDate = new Date();

        let minutes = nowDate.getMinutes();
        minutes = minutes < 10 ? '0' + minutes : minutes;

        $cloneRow.find('.msg_date').text(nowDate.getHours() + ':' + minutes);
        $cloneRow.insertAfter($dummyRow);
        let self = this;
        this.msgCounter++;
        this.find('.alert_msg_container').addClass('active');
        (function ($delRow) {
            setTimeout(() => {
                $delRow.remove();
                self.msgCounter--;
                if (self.msgCounter === 0) {
                    self.find('.alert_msg_container').removeClass('active');
                }
            }, 2000);
        })($cloneRow);
    }
}

app.registerGlobal(SdcAlertMessengerController);