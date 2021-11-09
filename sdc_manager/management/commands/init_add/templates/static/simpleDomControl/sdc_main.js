import {camelCaseToTagName, tagNameToCamelCase, getBody, uploadFileFormData} from "./sdc_utils.js";
import {
    replaceTagElementsInContainer,
    reloadHTMLController,
    DATA_CONTROLLER_KEY,
    CONTROLLER_CLASS
} from "./sdc_view.js";
import {AbstractSDC} from "./AbstractSDC.js";
import {Global, controllerList} from "./sdc_controller.js";
import {updateEvents} from "./sdc_dom_events.js";
import {trigger} from "./sdc_events.js";
import {isConnected} from "./sdc_socket.js";


export const app = {
    CSRF_TOKEN: window.CSRF_TOKEN || '',
    LANGUAGE_CODE: window.LANGUAGE_CODE || 'en',
    DEBUG: window.DEBUG || false,
    VERSION: window.VERSION || '0.0',
    tagNames: [],
    Global: Global,
    rootController: null,


    init_sdc: () => {
        isConnected();
        app.rootController = app.rootController || new AbstractSDC();
        app.tagNames = Object.keys(controllerList);
        replaceTagElementsInContainer(app.tagNames, getBody(), app.rootController);
    },

    controllerToTag: (Controller) => {
        let tagName = camelCaseToTagName(Controller.name);
        return tagName.replace(/-controller$/, '');
    },

    /**
     *
     * @param {AbstractSDC} Controller
     */
    registerGlobal: (Controller) => {
        let tagName = app.controllerToTag(Controller);
        let globalController = new Controller();
        controllerList[tagName] = [globalController, []];
        globalController._tagName = tagName;
        Global[tagNameToCamelCase(tagName)] = globalController;
    },

    /**
     *
     * @param {AbstractSDC} Controller
     */
    register: (Controller) => {
        let tagName = app.controllerToTag(Controller);
        controllerList[tagName] = [Controller, []];

        return {
            /**
             *
             * @param {Array<string>} mixins Controller tag names
             */
            addMixin: (...mixins) => {
                for (let mixin of mixins) {
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
     * @param {object} args
     * @return {Promise}
     */
    post: (controller, url, args) => {
        if (!args) {
            args = {};
        }

        args.CSRF_TOKEN = app.CSRF_TOKEN;
        return app.ajax(controller, url, params, $.post);
    },

    /**
     *
     * @param {AbstractSDC} controller
     * @param {string} url
     * @param {object} args
     * @return {Promise}
     */
    get: (controller, url, args) => {
        return app.ajax(controller, url, args, $.get);
    },

    /**
     *
     * @param {AbstractSDC} controller
     * @param {string} url
     * @param {object} args
     * @param {function} method $.get or $.post
     * @return {Promise}
     */
    ajax: (controller, url, args, method) => {
        if (!args) {
            args = {};
        }

        args.VERSION = app.VERSION;
        args._method = args._method || 'api';

        const p = new Promise((resolve, reject) => {
            return method(url, args).then((a, b, c) => {
                resolve(a, b, c);
                if (a.status === 'redirect') {
                    trigger('onNavLink', a['url-link']);
                } else {
                    p.then(() => {
                        app.refresh(controller.$container);
                    });
                }
            }).catch(reject);
        });

        return p;
    },

    submitFormAndUpdateView: (controller, form, url, method) => {
        let formData = new FormData(form);
        const p = new Promise((resolve, reject) => {
            uploadFileFormData(formData, (url || form.action), (method || form.method))
                .then((a, b, c) => {
                    resolve(a, b, c);
                    if (a.status === 'redirect') {
                        trigger('onNavLink', a['url-link']);
                    } else {
                        p.then(() => {
                            app.refresh(controller.$container);
                        });
                    }
                }).catch(reject);
        });

        return p;

    },
    submitForm: (form, url, method) => {
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
        if ($elem.hasClass(CONTROLLER_CLASS)) {
            return $elem.data(`${DATA_CONTROLLER_KEY}`);
        }
        return $elem.closest(`.${CONTROLLER_CLASS}`).data(`${DATA_CONTROLLER_KEY}`);
    },

    /**
     * safeEmpty removes all content of a dom
     * and deletes all child controller safely.
     *
     * @param $elem - jQuery DOM container to be emptyed
     */
    safeEmpty: ($elem) => {
        let $children = $elem.children();
        $children.each(function (_, element) {
            let $element = $(element);
            app.safeRemove($element);
        });

        return $elem;
    },

    /**
     * safeReplace removes all content of a dom
     * and deletes all child controller safely.
     *
     * @param $elem - jQuery DOM to be repleaced
     * @param $new - jQuery new DOM container
     */
    safeReplace: ($elem, $new) => {
        $new.insertBefore($elem);
        app.safeRemove($elem);
    },


    /**
     * safeRemove removes a dom and deletes all child controller safely.
     *
     * @param $elem - jQuery Dom
     */
    safeRemove: ($elem) => {
        $elem.each(function () {
            let $this = $(this);
            if ($this.hasClass(CONTROLLER_CLASS)) {
                $this.data(`${DATA_CONTROLLER_KEY}`).remove();
            }
        });

        $elem.find(`.${CONTROLLER_CLASS}`).each(function () {
            $(this).data(`${DATA_CONTROLLER_KEY}`).remove();
        });

        $elem.remove();
    },

    /**
     *
     * @param {AbstractSDC} controller
     * @return {Promise<jQuery>}
     */
    reloadController: (controller) => {
        return reloadHTMLController(controller).then((html) => {
            let $html = $(html);
            controller._childController = {};
            replaceTagElementsInContainer(app.tagNames, $html, controller).then(() => {
                app.safeEmpty(controller.$container);
                controller.$container.append($html);
                app.refresh(controller.$container, controller);
            });
        });
    },

    /**
     *
     * @param {jquery} $container
     * @param {AbstractSDC} leafController
     */
    refresh: ($container, leafController) => {
        if (!leafController) {
            leafController = app.getController($container);
        }

        let controller = leafController;
        let controllerList = [];
        while (controller) {
            controllerList.unshift(controller);
            controller = controller._parentController;
        }

        replaceTagElementsInContainer(app.tagNames, leafController.$container, leafController).then(() => {
            for (let con of controllerList) {
                updateEvents(con);
                con.onRefresh($container);
            }
        });
    },
};