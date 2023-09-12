import {allOff} from "./sdc_events.js";
import {app} from "./sdc_main.js";
import {callServer, Model} from "./sdc_socket.js";
import {uuidv4, setErrorsInForm, clearErrorsInForm, tagNameToCamelCase, tagNameToReadableName} from "./sdc_utils.js";

export class AbstractSDC {
    constructor() {
        this._uuid = uuidv4();
        this.contentUrl = '';
        this.contentReload = false;
        this.hasSubnavView = false;
        this.events = [];
        this.load_async = false;
        this.isEventsSet = false;
        this._allEvents = null;

        this._urlParams = [];
        this._models = [];

        // ------------------ Old deprecated properties ----------------------
        this._cssUrls = [];
        this.afterShow = () => {
            console.warn('afterShow is deprecated!!')
        };
        // -------------- End old deprecated properties ----------------------


        /**
         *
         * @type {{string: AbstractSDC}}
         */
        this._mixins = {};

        /**
         * @type {string}
         */
        this._tagName = '';

        /**
         * @type {{string:AbstractSDC}}
         */
        this._childController = {};

        /**
         * @type {AbstractSDC}
         */
        this._parentController = null;

        /**
         * @type {boolean}
         */
        this._onLoadDone = false;

        /**
         * @type {jquery}
         */
        this.$container = null;

        /**
         *
         * @type {boolean}
         */
        this._isMixin = false;
    }

    /**
     *
     * @param {string} method must be in {}
     * @param {Array} args in arguments of
     *
     */
    _runLifecycle(method, args) {
        if (app.DEBUG) {
            console.debug(method, this._tagName);
        }

        let returnPromisses = [];
        if (this._isMixin) {
            return;
        }
        this._isMixin = true;
        for (let mixinKey in this._mixins) {
            let mixin = this._mixins[mixinKey];
            if (typeof mixin[method] === 'function') {

                returnPromisses.push(mixin[method].apply(this, args));
            }
        }

        return Promise.all(returnPromisses).then(() => {
            this._isMixin = false;
        });
    }

    onInit() {
        if (app.DEBUG) {
            console.DEBUG(Array.apply(null, arguments), this._tagName);
        }
    }

    onLoad() {
        return this._runLifecycle('onLoad', arguments);
    }

    willShow() {
        return this._runLifecycle('willShow', arguments);
    }

    onRefresh() {
        return this._runLifecycle('onRefresh', arguments);
    }

    onRemove() {
        this._runLifecycle('onRemove', arguments)
        return true;
    }

    remove() {
        for (const model of this._models) {
            model.close();
        }
        let _childController = this._childController;
        for (let i in _childController) {
            if (_childController.hasOwnProperty(i)) {
                for (let cc of _childController[i]) {
                    if (!cc.remove()) {
                        return false;
                    }
                }
            }
        }

        if (!this.onRemove || this.onRemove()) {
            allOff(this);
            const c_name = tagNameToCamelCase(this._tagName);
            if (this._parentController._childController[c_name]) {
                let arr = this._parentController._childController[c_name];
                for (let i = 0; i < arr.length; i++) {
                    if (arr[i] === this) {
                        arr.splice(i, 1);
                    }
                }
            }

            this.$container.remove();
            delete this;
            return true;
        }

        return false;
    }

    controller_name() {
        return tagNameToReadableName(this._tagName);
    }

    addEvent(event, selector, handler) {
        this.getEvents();
        this._allEvents[event] = this._allEvents[event] || {};
        this._allEvents[event][selector] = handler;
    }

    getEvents() {
        if (this._allEvents) return this._allEvents;
        let allEvents = [];
        allEvents = allEvents.concat(this.events);
        for (let mixinKey in this._mixins) {
            let mixin = this._mixins[mixinKey];
            if (Array.isArray(mixin.events)) {
                allEvents = allEvents.concat(mixin.events)
            }
        }


        return (this._allEvents = Object.assign({}, ...allEvents));
    }

    post(url, args) {
        return app.post(this, url, args);
    }

    get(url, args) {
        return app.get(this, url, args);
    }

    submitForm(form, url, method) {
        return app.submitFormAndUpdateView(this, form, url, method);
    }

    serverCall(methode, args) {
        let re = /sdc_view\/([^/]+)/i;
        let app = this.contentUrl.match(re);
        if (!app || app.length < 2) {
            console.error('To use the serverCall function the contentUrl must be set: ' + this.name);
            return;
        }

        return callServer(app[1], this._tagName, methode, args);
    }

    /**
     *
     * @param model_name {string}
     * @param model_query {Object}
     * @constructor
     */
    newModel(model_name, model_query = {}) {
        let model = new Model(model_name, model_query);
        this._models.push(model);
        return model;
    }

    /**
     * Adapter to this.$container.find
     * @param {string} domSelector
     */
    find(domSelector) {
        return this.$container.find(domSelector);
    }

    refresh() {
        return app.refresh(this.$container, this);
    }

    reload() {
        return app.reloadController(this);
    }

    /**
     * Model Form Events
     */

    _submitModelForm($form, e) {
        let p_list = []
        if (!this._isMixin) {
            e.stopPropagation();
            e.preventDefault();
            let model = $form.data('model');
            const values = model.syncForm($form);
            for (let instance_value of values) {
                p_list.push(new Promise((resolve, reject) => {
                    let prom;
                    if(instance_value.pk !== null) {
                        prom = model.save(instance_value.pk);
                    } else {
                        prom = model.create(instance_value);
                    }

                    prom.then((res) => {
                        clearErrorsInForm($form);
                        resolve(res);
                    }).catch((data) => {
                        setErrorsInForm($form, $(data.html))
                        reject(data);
                    });
                }));
            }
        }

        return Promise.all(p_list).then((res) => {
            return Object.assign({}, ...res.flat());
        });
    }
}