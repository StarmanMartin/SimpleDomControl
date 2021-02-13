import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {trigger} from "../../../simpleDomControl/sdc_events.js";


class GSocketController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = '/sdc_view/sdc_tools/g_socket'; //<g-socket></g-socket>
        this._cssUrls.push('/static/sdc_tools/css/sdc/g_socket.css');

        this.game_id = null;
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
                    '/ws/' + self.game_id  + '/');
            } else {
                self.chatSocket = new WebSocket(
                    'ws://' + window.location.host +
                    '/ws/' + self.game_id + '/');
            }


            self.chatSocket.onmessage = function (e) {
                let data = JSON.parse(e.data);
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
                if(self._isConnected ) {
                    console.error('Socket closed unexpectedly');
                    self._isConnected = false;
                    setTimeout(() => {
                        self._connect();
                    }, 1000);
                }
            };

            self.chatSocket.onerror = function(err) {
                console.error('Socket encountered error: ', err.message, 'Closing socket');
                if(self._isConnected) {
                    try {
                        this.chatSocket.close();
                    } catch (e) {

                    }
                }
            };

            self.chatSocket.onopen = function () {
                self._isConnected = true;
                resolve(self.game_id);
            }
        })
    };

    send(msg) {
        this.isConnected().then(()=> {
            this.chatSocket.send(msg);
        })
    }


    close() {
        if(this._isConnected) {
            this.chatSocket.send('disconnect');
            this._isConnected = false;
            try {
                this.chatSocket.close();
            } catch (e) {

            }

        }
    }

    connect_to(game_id) {

        let check = game_id === this.game_id;
        if (!check) {
            this.game_id = game_id;
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
                return resolve(self.game_id);
            } else if (self.game_id !== null) {
                return resolve(self._connect());
            }

            console.error('Websocket rejected');
            reject();
        });
    };
}

app.registerGlobal(GSocketController);