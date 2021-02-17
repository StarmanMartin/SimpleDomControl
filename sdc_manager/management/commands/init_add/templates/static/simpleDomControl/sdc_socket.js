import {app} from './sdc_main.js';
import {trigger} from "./sdc_events.js";

let IS_CONNECTED = false;
let SDC_SOCKET = null

let OPEN_REQUESTS = [];

export function callServer(app, controller, funcName, args) {

    let id = OPEN_REQUESTS.length;

    SDC_SOCKET.send(JSON.stringify({
        event: 'sdc_call',
        id: id,
        controller: controller,
        app: app,
        function: funcName,
        args: args
    }));

    return {
        expect: (cb) => {
            OPEN_REQUESTS[id] = cb;
        }
    }
}

export function addGroup(group) {
    SDC_SOCKET.send(JSON.stringify({
        group: group,
        event: 'sdc_add_group'
    }));
}

export function removeGroup(group) {
    SDC_SOCKET.send(JSON.stringify({
        group: group,
        event: 'sdc_remove_group'
    }));
}

function _connect() {
    return new Promise((resolve) => {
        if (window.location.protocol === "https:") {
            SDC_SOCKET = new WebSocket( `wss://${window.location.host}/sdc_ws/ws/`);
        } else {
            SDC_SOCKET = new WebSocket(`ws://${window.location.host}/sdc_ws/ws/`);
        }


        SDC_SOCKET.onmessage = function (e) {
            let data = JSON.parse(e.data);
            if (data.is_error) {
                if (app.Global.gAlertMsg && (data.msg || data.header)) {
                    app.Global.gAlertMsg.push_error_msg(data.header || '', data.msg || '');
                }
            } else {
                if (app.Global.gAlertMsg && (data.msg || data.header)) {
                    app.Global.gAlertMsg.push_msg(data.header || '', data.msg || '');
                }

                if(data.type && data.type === 'sdc_recall') {
                    OPEN_REQUESTS[data.id](data.data);
                    delete OPEN_REQUESTS[data.id];
                } else if(data.type && data.type === 'sdc_event') {
                    let event = data.event;
                    if (event) {
                        trigger(event, data.payload);
                    }

                } else if(data.type && data.type === 'sdc_redirect') {
                    trigger('onNavLink', data.link);
                }
            }
        };

        SDC_SOCKET.onclose = function (e) {
            console.error('SDC Socket closed unexpectedly');
            IS_CONNECTED = false;
            setTimeout(() => {
                _connect();
            }, 1000);
        };

        SDC_SOCKET.onerror = function (err) {
            console.error('Socket encountered error: ', err.message, 'Closing socket');
            if (IS_CONNECTED) {
                try {
                    SDC_SOCKET.close();
                } catch (e) {

                }
            }
        };

        SDC_SOCKET.onopen = function () {
            IS_CONNECTED = true;
            resolve();
        }
    })
}

function close() {
    if (IS_CONNECTED) {
        IS_CONNECTED = false;
        try {
            SDC_SOCKET.close();
        } catch (e) {

        }

    }
}

export function isConnected() {

    return new Promise((resolve, reject) => {
        if (IS_CONNECTED) {
            return resolve();
        } else {
            return resolve(_connect());
        }
    });
}
