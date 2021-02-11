import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {trigger} from "../../../simpleDomControl/sdc_events.js";


class GSocketController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = '/sdc_view/sdc_tools/g_socket'; //<g-socket></g-socket>
        this._cssUrls.push('/static/sdc_tools/css/sdc/g_socket.css');

        this.user_id = -1;
        this.chatSocket = null;
        this._isConnected = false;

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
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    _connect() {
        let self = this;
        return new Promise((resolve) => {
            if (window.location.protocol === "https:") {
                self.chatSocket = new WebSocket(
                    'wss://' + window.location.host +
                    '/ws/' + self.user_id  + '/');
            } else {
                self.chatSocket = new WebSocket(
                    'ws://' + window.location.host +
                    '/ws/' + self.user_id + '/');
            }


            self.chatSocket.onmessage = function (e) {
                var data = JSON.parse(e.data);
                if (data.is_error) {
                    if (data.msg || data.header) {
                        app.Global.gAlertMsg.push_error_msg(data.header || '', data.msg || '');
                    }
                } else {
                    if (data.msg || data.header) {
                        app.Global.gAlertMsg.push_msg(data.header || '', data.msg || '');
                    }

                    let event = data.type;
                    if(data.controller) {
                        event = data.controller.replace(/-/g, '_') + '_' + event;
                    }

                    trigger(event, data);
                }
            };

            self.chatSocket.onclose = function (e) {
                console.error('Socket closed unexpectedly');
                this._isConnected = false;
                setTimeout(() => {
                    connect(self);
                }, 1000);
            };

            self.chatSocket.onerror = function(err) {
                console.error('Socket encountered error: ', err.message, 'Closing socket');
                self.chatSocket.close();
            };

            self.chatSocket.onopen = function () {
                self._isConnected = true;
                resolve(self.user_id);
            }
        })
    };

    close() {
        if(this._isConnected) {
            this._isConnected = false;
            try {
                this.chatSocket.close();
            } catch (e) {

            }

        }
    }

    connect_to(user_id) {

        let check = user_id === this.user_id;
        if (!check) {
            user_id = parseInt(user_id, 10);
            if (!isNaN(user_id)) {
                this.user_id = user_id;
            }

            if (this._isConnected) {
                this.close();
            }
        }

        return this.isConnected();
    };

    isConnected() {
        let self = this;
        return new Promise((resolve, reject) => {
            if (self._isConnected) {
                return resolve(self.user_id);
            } else if (self.user_id >= 0) {
                return resolve(self._connect(self));
            }

            console.error('Websocket rejected');
            reject();
        });
    };
}

app.registerGlobal(GSocketController);