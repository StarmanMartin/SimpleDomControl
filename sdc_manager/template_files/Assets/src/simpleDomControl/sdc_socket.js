import {app} from './sdc_main.js';
import {trigger} from "./sdc_events.js";
import {uuidv4} from "./sdc_utils";

let IS_CONNECTED = true;
let SDC_SOCKET = null
const MAX_FILE_UPLOAD = 25000;
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
        this.on_update = () => {
        };
        this.on_create = () => {
        };

        this.form_id = uuidv4();
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
        if (pk !== null) {
            let elem = this.values_list.find(elm => elm.pk === pk);
            if (!elem) {
                elem = {pk: pk};
                this.values_list.push(elem);
            }
            return elem;
        }
        return {pk: pk};

    }

    filter(model_query) {
        this.model_query = Object.assign({}, this.model_query, model_query);
        return this;
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

    detailView(pk = -1) {
        let $div_list = $('<div>');

        let load_promise;
        if (this.values_list.length !== 0) {
            load_promise = this.isConnected();
        } else {
            load_promise = this.load();
        }

        load_promise.then(() => {
            if (pk === -1) {
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

    syncFormToModel($forms) {
        return this.syncForm($forms);
    }

    syncModelToForm($forms) {
        if (!$forms || !$forms.hasClass(this.form_id)) {
            $forms = $(`.${this.form_id}`);
        }
        document.getElementById('ö').hasAttribute()
        let self = this;
        $forms.each(function () {
            if(!this.hasAttribute('data-model_pk')) {
                return;
            }
            let pk = $(this).data('model_pk');
            let instance = self.byPk(pk);
            for (let form_item of this.elements) {
                let name = form_item.name;
                if (name && name !== '') {
                    if (form_item.type === 'checkbox') {
                        form_item.checked = instance[name];
                    } else if (form_item.type === 'file' && instance[name] instanceof File) {
                        let container = new DataTransfer();
                        container.items.add(file);
                        form_item.files = container;
                    } else {
                        $(form_item).val(instance[name]);
                    }
                }
            }
        });

    }

    syncForm($forms) {
        if (!$forms || !$forms.hasClass(this.form_id)) {
            $forms = $(`.${this.form_id}`);
        }

        const self = this;
        let instances = [];
        let p_list = [];

        $forms.each(function () {
            let $form = $(this);
            let pk = $form.data('model_pk');
            let instance = self.byPk(pk);
            for (let form_item of this.elements) {
                let name = form_item.name;
                if (name && name !== '') {
                    if (form_item.type === 'checkbox') {
                        instance[name] = form_item.checked;
                    } else if (form_item.type === 'file') {
                        instance[name] = form_item.files[0];
                    } else {
                        instance[name] = $(form_item).val();
                    }
                }
            }

            instances.push(instance);
            return instance;
        });

        if (this.values_list.length <= 1 && instances.length > 0) {
            this.values = instances.at(-1);
        }

        return instances;

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
                    let $form = $div_form.closest('form').addClass(`sdc-model-create-form sdc-model-form ${this.form_id}`).data('model', this).data('model_pk', null);
                    if (!$form[0].hasAttribute('sdc_submit')) {
                        $form.attr('sdc_submit', 'submitModelForm')
                    }

                    app.refresh($div_form);
                    resolve(data);
                }, reject];
            });

        });

        return $div_form;
    }

    editForm(pk = -1) {
        let load_promise;
        if (this.values_list.length !== 0) {
            load_promise = this.isConnected();
        } else {
            load_promise = this.load();
        }

        let $div_form = $('<div>');

        load_promise.then(() => {
            if (pk <= -1) {
                pk = this.values_list.at(pk).pk;
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
                    let $form = $div_form.closest('form').addClass(`sdc-model-edit-form sdc-model-form ${this.form_id}`).data('model', this).data('model_pk', pk);
                    if (!$form[0].hasAttribute('sdc_submit')) {
                        $form.attr('sdc_submit', 'submitModelForm')
                    }

                    app.refresh($div_form);
                    resolve(data);
                }, reject];
            });

        });

        return $div_form;
    }

    save(pk = -1) {
        return this.isConnected().then(() => {
            let elem_list;
            if (pk > -1) {
                elem_list = [this.byPk(pk)];
            } else {
                elem_list = this.values_list;
            }
            let p_list = []
            elem_list.forEach((elem) => {
                const id = uuidv4();
                p_list.push(new Promise((resolve, reject) => {
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

                    this.open_request[id] = [(res) => {
                        let data = JSON.parse(res.data.instance);
                        this._parseServerRes(data);
                    }, reject];
                }));
            });

            return Promise.all(p_list);
        });
    }

    create(values) {
        const id = uuidv4();
        return this.isConnected().then(() => {
            return new Promise((resolve, reject) => {
                this._readFiles(values).then((files) => {
                    this.socket.send(JSON.stringify({
                        event: 'model',
                        event_type: 'create',
                        event_id: id,
                        args: {
                            model_name: this.model_name,
                            model_query: this.model_query,
                            data: values,
                            files: files
                        }
                    }));

                    this.open_request[id] = [(res) => {
                        let data = JSON.parse(res.data.instance);
                        this._parseServerRes(data);
                        resolve(res);
                    }, reject];
                })
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

    close() {
        if (this.socket) {
            this._auto_reconnect = false;
            this.socket.onclose = () => {
            };
            this.socket.close();
            delete this['socket'];
        }
    }

    _readFiles(elem) {
        let to_solve = [];
        let files = {}
        for (const [key, value] of Object.entries(elem)) {
            if (value instanceof File) {
                to_solve.push(new Promise((resolve, reject) => {
                    ((key, value) => {
                        let reader = new FileReader();
                        reader.onload = e => {
                            const id = uuidv4();
                            this.open_request[id] = [resolve, reject];

                            let result = e.target.result;
                            let number_of_chunks = parseInt(Math.ceil(result.length / MAX_FILE_UPLOAD));
                            files[key] = {
                                id: id,
                                file_name: value.name,
                                field_name: key,
                                content_length: value.size,
                            };
                            for (let i = 0; i < number_of_chunks; ++i) {
                                this.socket.send(JSON.stringify({
                                    event: 'model',
                                    event_type: 'upload',
                                    event_id: id,
                                    args: {
                                        chunk: result.slice(MAX_FILE_UPLOAD * i, MAX_FILE_UPLOAD * (i + 1)),
                                        idx: i,
                                        number_of_chunks: number_of_chunks,
                                        file_name: value.name,
                                        field_name: key,
                                        content_length: value.size,
                                        content_type: value.type,
                                        model_name: this.model_name,
                                        model_query: this.model_query
                                    }
                                }));
                            }
                        }
                        reader.onerror = e => {
                            reject()
                        };
                        reader.readAsBinaryString(value);
                    })(key, value);
                }))
            }
        }

        return Promise.all(to_solve).then(() => {
            return files
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
                const json_res = JSON.parse(data.args.data);
                this.values_list = [];
                this._parseServerRes(json_res);

            } else if (data.type === 'on_update' || data.type === 'on_create') {
                const json_res = JSON.parse(data.args.data);

                let obj = this._parseServerRes(json_res);
                let cb;

                if (data.type === 'on_create') {
                    cb = this.on_create;
                } else {
                    cb = this.on_update;
                }

                cb(obj);

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

    _parseServerRes(res) {
        let updated = []
        for (let json_data of res) {
            const pk = json_data.pk
            const obj = this.byPk(pk);
            for (const [k, v] of Object.entries(json_data.fields)) {
                obj[k] = v;
            }

            updated.push(obj);
        }

        if (this.values_list.length === 1) {
            this.values = this.values_list.at(-1);
        } else {
            this.values = {};
        }

        return updated;

    }
}