import {camelCaseToTagName, getBody, uploadFileFormData} from "./sdc_utils.js";
import {replaceTagElementsInContainer, DATA_CONTROLLER_KEY, CONTROLLER_CLASS} from "./sdc_view.js";
import {AbstractSDC} from "./AbstractSDC.js";
import {Global, controllerList} from "./sdc_controller.js";
import {updateEvents} from "./sdc_dom_events.js";


export const app = {
    CSRF_TOKEN: window.CSRF_TOKEN || '',
    LANGUAGE_CODE: window.LANGUAGE_CODE || 'en',
    DEBUG: window.DEBUG || false,
    VERSION: window.VERSION || '0.0',
    tagNames: [],
    Global: Global,
    rootController: null,


    init_sdc: () => {
        "use strict"
        app.rootController = app.rootController || new AbstractSDC();
        app.tagNames = Object.keys(controllerList);
        replaceTagElementsInContainer(app.tagNames, getBody(), app.rootController);
    },

    controllerToTag: (Controller) => {
        "use strict"
        let tagName = camelCaseToTagName(Controller.name);
        return tagName.replace(/-controller$/, '');
    },

    /**
     *
     * @param {AbstractSDC} Controller
     */
    registerGlobal: (Controller) => {
        "use strict"
        let tagName = app.controllerToTag(Controller);
        let globalController = new Controller();
        controllerList[tagName] = [new globalController(), true];
        globalController._tagName = tagName;
        Global[tagName] = globalController;
    },

    /**
     *
     * @param {AbstractSDC} Controller
     */
    register: (Controller) => {
        "use strict"
        let tagName = app.controllerToTag(Controller);
        controllerList[tagName] = [Controller, []];

        return {
            addMixin:(...mixins)=> {
                for(let mixin of mixins) {
                    let mixinName = camelCaseToTagName(mixin);
                    controllerList[tagName][1].push(mixinName);
                }
            }
        }
    },

    /**
     *
     * @param {AbstractSDC} controller
     * @param {string} url
     * @param {object} params
     * @return {Promise}
     */
    post: (controller, url, params) => {
        "use strict"
        return app.ajax(controller, url, params, $.post);
    },

    /**
     *
     * @param {AbstractSDC} controller
     * @param {string} url
     * @param {object} params
     * @return {Promise}
     */
    get: (controller, url, params) => {
        "use strict"
        return app.ajax(controller, url, params, $.get);
    },

    /**
     *
     * @param {AbstractSDC} controller
     * @param {string} url
     * @param {object} params
     * @param {function} method $.get or $.post
     * @return {Promise}
     */
    ajax: (controller, url, params, method) => {
        "use strict"
        const p = new Promise((resolve, reject) => {
            return method(url, params).then((a, b, c) => {
                resolve(a, b, c);
                p.then(() => {
                    app.refresh(controller.$container);
                });
            }).catch(reject);
        });

        return p;
    },

    submitFormAndUpdateView: (form, url, method) => {
        "use strict"
        let formData = new FormData(form);
        const p = new Promise((resolve, reject) => {
            uploadFileFormData(formData, (url || form.action), (method || form.method))
                .then((a, b, c) => {
                    resolve(a, b, c);
                    p.then(() => {
                        app.refresh($(form));
                    });
                }).catch(reject);
        });

        return p;

    },
    submitForm: (form, url, method) => {
        "use strict"
        let formData = new FormData(form);
        return new Promise((resolve, reject) => {
            uploadFileFormData(formData, (url || form.action), (method || form.method))
                .then(resolve).catch(reject);
        });
    },

    /**
     *
     * @param {jquery} $elem
     * @return {AbstractSDC}
     */
    getController: ($elem) => {
        "use strict"
        return $elem.closest(`.${CONTROLLER_CLASS}`).data(`${DATA_CONTROLLER_KEY}`);
    },

    /**
     *
     * @param {jquery} $container
     */
    refresh: ($container) => {
        "use strict"
        let leafController = app.getController($container);
        let controller = leafController;
        let controllerList = [];
        while (controller) {
            controllerList.unshift(controller);
            controller = controller._parentController;
        }

        replaceTagElementsInContainer(app.tagNames, leafController.$container, leafController).then(()=> {
            for (let con of controllerList) {
                updateEvents(con);
            }
        });
    },
};