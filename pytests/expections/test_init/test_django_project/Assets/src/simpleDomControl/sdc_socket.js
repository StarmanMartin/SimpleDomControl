import {app} from './sdc_main.js';
import {trigger} from "./sdc_events.js";
import {uuidv4} from "./sdc_utils";

let IS_CONNECTED = true;
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

function _connect() {
    return new Promise((resolve) => {
        if (window.location.protocol === "https:") {
            SDC_SOCKET = new WebSocket(`wss://${window.location.host}/sdc_ws/ws/`);
        } else {
            SDC_SOCKET = new WebSocket(`ws://${window.location.host}/sdc_ws/ws/`);
        }


        SDC_SOCKET.onmessage = function (e) {
            let data = JSON.parse(e.data);
            if (data.is_error) {
                if (app.Global.sdcAlertMessenger && (data.msg || data.header)) {
                    app.Global.sdcAlertMessenger.pushErrorMsg(data.header || '', data.msg || '');
                }
            } else {
                if (app.Global.sdcAlertMessenger && (data.msg || data.header)) {
                    app.Global.sdcAlertMessenger.pushMsg(data.header || '', data.msg || '');
                }

                if (data.type && data.type === 'sdc_recall') {
                    OPEN_REQUESTS[data.id](data.data);
                    delete OPEN_REQUESTS[data.id];
                } else if (data.type && data.type === 'sdc_event') {
                    let event = data.event;
                    if (event) {
                        trigger(event, data.payload);
                    }

                } else if (data.type && data.type === 'sdc_redirect') {
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

export class Model {
    /**
     *
     * @param model_name {string}
     * @param model_query {json}
     */
    constructor(model_name, model_query = {}) {
        this.values_list = [];
        this.values = {};
        this.model_name = model_name;
        this.model_query = model_query;
        this._is_connected = false;
        this._is_conneting_process = false;
        this._auto_reconnect = true;
        this.socket = null;
        this.open_request = {};
        this.on_update = () => {};
        this.on_create = () => {};
    }

    [Symbol.iterator]() {
        let idx = 0;
        return {
            next: function () {
                if (idx < this.values_list) {
                    ++idx;
                    return {value: this.values_list[idx], done: false};
                }
                return {value: null, done: true};
            }
        };
    }

    byPk(pk) {
        let elem = this.values_list.find(elm => elm.pk === pk)
        if (!elem) {
            elem = {pk: pk}
            this.values_list.push(elem);
        }
        return elem;
    }

    load() {
        return this.isConnected().then(() => {
            const id = uuidv4();
            return new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'load',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query
                    }
                }));

                this.open_request[id] = [resolve, reject];
            });
        });
    }

    listView(filter = {}) {
        let $div_list = $('<div>');
        this.isConnected().then(() => {
            const id = uuidv4();
            new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'list_view',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query,
                        filter: filter
                    }
                }));

                this.open_request[id] = [(data) => {
                    $div_list.append(data.html);
                    app.refresh($div_list);
                    resolve(data);
                }, reject];
            });

        });

        return $div_list;
    }

    detailView(pk=-1) {
        let $div_list = $('<div>');

        let load_promise;
        if (this.values_list.length !== 0) {
            load_promise = this.isConnected();
        } else {
            load_promise = this.load();
        }

        load_promise.then(() => {
            if(pk === -1) {
                pk = this.values_list[0].pk
            }
            const id = uuidv4();
            new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'detail_view',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query,
                        pk: pk
                    }
                }));

                this.open_request[id] = [(data) => {
                    $div_list.append(data.html);
                    app.refresh($div_list);
                    resolve(data);
                }, reject];
            });

        });

        return $div_list;
    }

    createForm() {
        let $div_form = $('<div>');
        this.isConnected().then(() => {
            const id = uuidv4();
            new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'create_form',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query
                    }
                }));

                this.open_request[id] = [(data) => {
                    $div_form.append(data.html);
                    let $form = $div_form.closest('form').addClass('sdc-model-create-form sdc-model-form').data('model', this);
                    if (!$form[0].hasAttribute('sdc_submit')) {
                        $form.attr('sdc_submit', 'submitCreateForm')
                    }

                    app.refresh($div_form);
                    resolve(data);
                }, reject];
            });

        });

        return $div_form;
    }

    editForm(pk = -1, idx = -1) {
        let load_promise;
        if (this.values_list.length !== 0) {
            load_promise = this.isConnected();
        } else {
            load_promise = this.load();
        }

        let $div_form = $('<div>');

        load_promise.then(() => {
            if (pk <= -1) {
                pk = this.values_list.at(idx).pk;
            }

            const id = uuidv4();
            new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'edit_form',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query,
                        pk: pk
                    }
                }));

                this.open_request[id] = [(data) => {
                    $div_form.append(data.html);
                    let $form = $div_form.closest('form').addClass('sdc-model-edit-form sdc-model-form').data('model', this).data('model_pk', pk);
                    if (!$form[0].hasAttribute('sdc_submit')) {
                        $form.attr('sdc_submit', 'submitEditForm')
                    }

                    app.refresh($div_form);
                    resolve(data);
                }, reject];
            });

        });

        return $div_form;
    }

    save(pk = -1, idx = -1) {
        return this.isConnected().then(() => {
            let elem;
            if (pk > -1) {
                elem = this.byPk(pk);
            } else {
                elem = this.values_list.at(idx);
            }
            const id = uuidv4();
            return new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'save',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query,
                        data: elem
                    }
                }));

                this.open_request[id] = [resolve, reject];
            });
        });
    }

    create(values) {
        const id = uuidv4();
        return this.isConnected().then(() => {
            return new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'create',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query,
                        data: values
                    }
                }));

                this.open_request[id] = [resolve, reject];
            });
        });
    }

    delete(pk) {
        const id = uuidv4();
        return this.isConnected().then(() => {
            return new Promise((resolve, reject) => {
                this.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'delete',
                    event_id: id,
                    args: {
                        model_name: this.model_name,
                        model_query: this.model_query,
                        pk: pk
                    }
                }));

                this.open_request[id] = [resolve, reject];
            });
        });
    }

    isConnected() {
        return new Promise((resolve, reject) => {
            if (this._is_connected) {
                resolve();
            } else if (!this._is_conneting_process) {
                this._is_conneting_process = true;
                this.open_request['_connecting_process'] = [() => {
                }, () => {
                }]
                this._connectToServer().then(() => {
                    resolve(this._checkConnection());
                });
            } else {
                const [resolve_origin, reject_origin] = this.open_request['_connecting_process'];
                this.open_request['_connecting_process'] = [
                    () => {
                        resolve_origin();
                        resolve();
                    },
                    () => {
                        reject_origin();
                        reject();
                    }
                ]
            }
        });
    }

    _onMessage(e) {
        let data = JSON.parse(e.data);
        if (data.is_error) {
            if (this.open_request.hasOwnProperty(data.event_id)) {
                this.open_request[data.event_id][1](data);
                delete this.open_request[data.event_id];
            }
            if (app.Global.sdcAlertMessenger && (data.msg || data.header)) {
                app.Global.sdcAlertMessenger.pushErrorMsg(data.header || '', data.msg || '');
            }
            if (data.type === 'connect') {
                this.open_request['_connecting_process'][1](data);
                delete this.open_request['_connecting_process'];
                this._auto_reconnect = false;
                this.socket.close();
            }
        } else {
            if (app.Global.sdcAlertMessenger && (data.msg || data.header)) {
                app.Global.sdcAlertMessenger.pushMsg(data.header || '', data.msg || '');
            }
            if (data.type === 'connect') {
                this._is_connected = true;
                this._is_conneting_process = false;
                this.open_request['_connecting_process'][0](data);
                delete this.open_request['_connecting_process'];
            } else if (data.type === 'load') {
                const json_data = JSON.parse(data.args.data);
                this.values_list = [];
                for (const [k, v] of Object.entries(json_data)) {
                    this.values_list.push(Object.assign({}, v.fields, {pk: v.pk}));
                }
                if (json_data.length === 1) {
                    this.values = this.values_list.at(-1);
                }

            } else if (data.type === 'on_update' || data.type === 'on_create') {
                const json_data = JSON.parse(data.args.data);

                const pk = json_data[0].pk;
                let obj, cb;

                if (data.type === 'on_create') {
                    obj = {pk: pk};
                    this.values_list.push(obj);
                    cb = this.on_create;
                    if (this.values_list.length === 1) {
                        this.values = this.values_list.at(-1);
                    } else {
                        this.values = {};
                    }
                } else {
                    obj = this.byPk(pk);
                    cb = this.on_update;
                }

                for (const [k, v] of Object.entries(json_data[0].fields)) {
                    obj[k] = v;
                }

                cb(json_data);

            }
            if (this.open_request.hasOwnProperty(data.event_id)) {
                this.open_request[data.event_id][0](data);
                delete this.open_request[data.event_id];
            }
        }
    }

    _connectToServer() {
        return new Promise((resolve) => {

            const model_identifier = `${this.model_name}` + (this.model_id > 0 ? `/${this.model_id}` : '');
            if (window.location.protocol === "https:") {
                this.socket = new WebSocket(`wss://${window.location.host}/sdc_ws/model/${model_identifier}`);
            } else {
                this.socket = new WebSocket(`ws://${window.location.host}/sdc_ws/model/${model_identifier}`);
            }


            this.socket.onmessage = this._onMessage.bind(this);

            this.socket.onclose = (e) => {
                console.error(`SDC Model (${this.model_name}, ${this.model_id}) Socket closed unexpectedly`);
                this._is_connected = false;
                for (const [key, value] of Object.entries(this.open_request)) {
                    value[1](e);
                }
                this.open_request = {};

                setTimeout(() => {
                    if (this._auto_reconnect) {
                        this._connectToServer().then(() => {
                        });
                    }
                }, 1000);
            };

            this.socket.onerror = (err) => {
                console.error(`Model Socket encountered error: ${err} Closing socket`);
                if (this._is_connected) {
                    try {
                        this.socket.close();
                    } catch (e) {

                    }
                }
            };


            this.socket.onopen = () => {
                resolve();
            }
        });

    }

    _checkConnection() {
        const id = uuidv4();
        return new Promise((resolve, reject) => {
            this.socket.send(JSON.stringify({
                event: 'model',
                event_type: 'connect',
                event_id: id,
                args: {
                    model_name: this.model_name,
                    model_query: this.model_query
                }
            }));

            this.open_request[id] = [resolve, reject];
        });
    }

    close() {
        if(this.socket) {
            this._auto_reconnect = false;
            this.socket.onclose = () => {
            };
            this.socket.close();
            delete this['socket'];
        }
    }
}