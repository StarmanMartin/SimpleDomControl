import {camelCaseToTagName, getBody, uploadFileFormData} from "./sdc_utils.js";
import {replaceTagElementsInContainer, DATA_CONTROLLER_KEY, CONTROLLER_CLASS} from "./sdc_view.js";
import {AbstractSDC} from "./AbstractSDC.js";
import {Global, controllerList} from "./sdc_controller.js";
import {updateEvents} from "./sdc_dom_events.js";

export const app = {
    VERSION: '0.0',
    tagNames: [],
    Global: Global,
    rootController: null,


    init_sdc: () => {
        app.rootController = app.rootController || new AbstractSDC();
        app.tagNames = Object.keys(controllerList);
        replaceTagElementsInContainer(app.tagNames, getBody(), app.rootController);
    },

    /**
     *
     * @param {AbstractSDC} Controller
     */
    registerGlobal: (Controller) => {
        let tagName = camelCaseToTagName(Controller.name);
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
        let tagName = camelCaseToTagName(Controller.name);
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

    post: (url, params) => {
        return app.ajax(url, params, $.post);
    },

    get: (url, params) => {
        return app.ajax(url, params, $.get);
    },

    ajax: (url, params, method) => {
        const p = new Promise((resolve, reject) => {
            return method(url, params).then((a, b, c) => {
                re
                solve(a, b, c);
                p.then(() => {
                    app.refresh($(form));
                });
            }).catch(reject);
        });

        return p;
    },

    submitFormAndUpdateView: (form, url, method) => {
        var formData = new FormData(form);
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
        var formData = new FormData(form);
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
        return $elem.closest(`.${CONTROLLER_CLASS}`).data(`${DATA_CONTROLLER_KEY}`);
    },

    /**
     *
     * @param {jquery} $container
     */
    refresh: ($container) => {
        let leafController;
        let controller = leafController = app.getController($container);
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