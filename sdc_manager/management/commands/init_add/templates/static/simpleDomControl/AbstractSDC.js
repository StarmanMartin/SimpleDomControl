import {allOff} from "./sdc_events.js";

export class AbstractSDC {
    contentUrl = '';
    contentReload = false;

    _events = [];

    _cssUrls = [];

    _urlParams = [];


    /**
     *
     * @type {{string: AbstractSDC}}
     */
    _mixins = {};

    /**
     * @type {string}
     */
    _tagName = '';

    /**
     * @type {{string:AbstractSDC}}
     */
    _childController = {};

    /**
     * @type {AbstractSDC}
     */
    _parentController = null;

    /**
     * @type {boolean}
     */
    _onLoadDone = false;

    /**
     * @type {jquery}
     */
    $container = null;

    /**
     *
     * @type {boolean}
     */
    _isMixin = false;

    constructor() {
    }

    get cssUrls() {
        let allCssUrls = this._cssUrls;
        if (typeof allCssUrls === "string") {
            allCssUrls = [allCssUrls];
        }

        if(this._isMixin) {
            return allCssUrls;
        }

        for(let mixinKey in this._mixins) {
            let mixin = this._mixins[mixinKey];
            allCssUrls = allCssUrls.concat(mixin._cssUrls);
        }

        return allCssUrls;
    }

    get events() {
        let events = this._events;

        for(let mixinKey in this._mixins) {
            let mixin = this._mixins[mixinKey];
            events = events.concat(mixin._events);
        }

        return events;
    }

    /**
     *
     * @param {string} method must be in {}
     * @param {Array} args in arguments of
     *
     */
    _runLifecycle(method, args) {
        console.log(method, this._isMixin);
        let returnPromisses = [];
        if(this._isMixin) {
            return;
        }
        this._isMixin = true;
        for(let mixinKey in this._mixins) {
            let mixin = this._mixins[mixinKey];
            if(typeof mixin[method] === 'function') {

                returnPromisses.push(mixin[method].apply(this, args));
            }
        }

        return Promise.all(returnPromisses).then(() => {
            this._isMixin = false;
        });
    }

    onInit() {
        return;
    }

    onLoad() {
        return this._runLifecycle('onLoad', arguments);
    }

    willShow() {
        return this._runLifecycle('willShow', arguments);
    }

    afterShow() {
        return this._runLifecycle('afterShow', arguments);
    }

    onRemove() {
        this._runLifecycle('onRemove', arguments)
        return true;
    }

    remove() {
        let _childController = this._childController;
        for (let i in _childController) {
            if (_childController.hasOwnProperty(i)){
                for(let cc of _childController[i]) {
                    if (!cc.remove()) {
                        return false;
                    }
                }
            }
        }

        if (!this.onRemove || this.onRemove()) {
            allOff(this);
            if (this._parentController._childController[this._tagName]) {
                delete this._parentController._childController[this._tagName];
            }

            this.$container.remove();
            return true;

        }

        return false;
    }

}