(function (app) {
    "use strict";
    /**
     * sets debug mode
     * @type {boolean}
     */
    let debug = true;

    /**
     * The number of all controller
     * @type {number}
     */
    let controllerAmount = 0;

    /**
     * The public controllerManager objects
     * @type {{
     * runControlFlowFunctions: function,
     * registerController: function,
     * registerGlobalController: function,
     * controllerFactory: function,
     * GlobalController: {},
     * onComponentLoadHandlerList: []
     * }}
     */
    let cm = app.controllerManager = {};

    /**
     * A list with all handler function getting called when
     * all components are ready.
     * @type {Array}
     */
    cm.onComponentLoadHandlerList = [];

    /**
     * globalController Class list. Key is tag name as string.
     * @type {{}}
     */
    let gcl = cm.GlobalController = {};

    /**
     * List contains super controller.
     * If a super tag is registered by controller registration .
     * @type {{}}
     */
    let defaultSuperTags = {};

    /**
     * globalControllerInstance instance list. Key is tag name as string.
     * @type {{}}
     */
    let globalControllerInstance = {};

    /**
     * controllerList Class list. Key is tag name as string.
     * @type {{}}
     */
    let controllerList = {};

    /**
     * A list with the names of the simple control flow function
     * @type {string[]}
     */
    let controlFunctions = ['willShow', 'afterShow', 'onRemove'];

    /**
     * Tag name for contorller already loaded.
     * @type {string}
     */
    let tagOnLoadDone = '__dom_on_load_tag_key';

    /**
     * A list with the names of the all controller propeties
     * @type {string[]}
     */
    let controlProperties = [tagOnLoadDone, '_urlParams', 'onLoad', 'onInit', '$content', '$container', 'super', 'events', 'parentController', 'contentUrl', 'cssUrls'].concat(controlFunctions);


    /**
     * setParentController sets the parent controller as property: 'parentController'
     * to the child controller. Also it adds the child controller to the property list:
     * 'parentController' to the parent controller
     *
     * @param parentController - js controller instance, controller of the parent DOM of the controllers DOM
     * @param controller - js controller instance
     * @return {*} - parentController
     */
    function setParentController(parentController, controller) {
        if (parentController) {
            if (!parentController.childController) {
                parentController.childController = [];
            }

            parentController.childController.push(controller);
        }

        controller.childController = [];
        return (controller.parentController = parentController)
    }

    /**
     * wrapSuperOnLoadFunction wraps the control flow function onLoad of the controller
     * by the onLoad function of the super controller.
     *
     * @param controller - js controller instance
     * @param superController - js controller instance
     */
    function wrapSuperOnLoadFunction(controller, superController) {
        let originFunction = controller.onLoad;
        controller.onLoad = function () {
            let args = arguments;
            let contentUrlOrigin = controller.contentUrl,
                cssUrlsOrigin = controller.cssUrls;
            controller.contentUrl = superController.contentUrl;
            controller.cssUrls = superController.cssUrls;

            return superController.onLoad.apply(controller, args).then(function (result) {
                controller.contentUrl = contentUrlOrigin;
                controller.cssUrls = cssUrlsOrigin;
                if (result) {
                    controller.$content = result;
                }

                return originFunction.apply(controller, args);
            });
        };
    }

    /**
     * wrapSuperControlFlowFunctions wraps the control flow functions
     * willShow, afterShow and onRemove
     * of the controller by the control flow functions of the super controller.
     *
     * @param controller - js controller instance
     * @param superController - js controller instance
     */
    function wrapSuperControlFlowFunctions(controller, superController) {
        let restControls = controlFunctions;
        let runWrapSuperControlFlowFunctions = function (fieldName, controller) {
            if (!superController[fieldName]) {
                return;
            }
            if (!controller[fieldName]) {
                controller[fieldName] = superController[fieldName];
                return;
            }

            let originFunction = controller[fieldName];
            controller[fieldName] = function () {
                let args = arguments;
                return new Promise(function (resolve) {
                    resolve(superController[fieldName].apply(controller, args))
                }).then(function () {
                    return originFunction.apply(controller, args);
                });
            }
        };

        for (let i = 0; i < restControls.length; i++) {
            runWrapSuperControlFlowFunctions(restControls[i], controller);

        }
    }

    /**
     * extendSuperControlFunctions Extends all functions and properties from
     * the super controller. The control flow functions:
     * -onload, -willShow, -afterShow, -onRemove;
     * will be wrapped
     *
     * @param controller - js controller instance
     * @param superController - js controller instance
     */
    function extendSuperControlFunctions(controller, superController) {
        for (let _superFields in superController) {
            let superFields;
            if (superController.hasOwnProperty(_superFields) || true) {
                superFields = _superFields;
            }
            if (controlProperties.indexOf(superFields) === -1
                && (superController[superFields] || superController.hasOwnProperty(superFields))
                && !controller[superFields] && !controller.hasOwnProperty(superFields)) {
                controller[superFields] = superController[superFields];
            }
        }

        controller.events.unshift(superController.events || {});
        wrapSuperOnLoadFunction(controller, superController);
        wrapSuperControlFlowFunctions(controller, superController);
    }

    /**
     * controllerFactoryInstance it generates a controller instance
     * depending if the controller is registered as a global controller. It sets the
     * $container object to the jQuery representation of the tag.
     *
     * It handles the init parameter by the data values of the DOM.
     *
     * It handles the super extensions.
     *
     * @param parentController - Controller of the parent DOM
     * @param $element - The current DOM jQuery
     * @param tagName - the registered tag name of the current DOM
     * @param superTagNameList - tag names of super controller
     * @return {controller} -  new Controller
     */
    function controllerFactoryInstance(parentController, $element, tagName, superTagNameList) {
        let controller = new controllerList[tagName]();
        setParentController(parentController, controller);

        controller.events = [controller.events || {}];
        let tempController = controller;
        tempController.$container = $element;
        for (let i = 0; i < superTagNameList.length; i++) {
            let superTagName = superTagNameList[i];
            let superController = new controllerList[superTagName]();

            superController.$container = $element;
            tempController.super = superController;
            tempController = superController;
            extendSuperControlFunctions(controller, superController);
        }

        app.paramManager.runOnInitWithParameter(controller, $element);

        return controller;
    }

    /**
     * checkIfAllControllerRegistered simply checks if the number of registered
     * controller is as much as the number of total controller. If done it starts
     * parsing the page.
     */
    function checkIfAllControllerRegistered() {
        if (app.domRouter.tagList.length === controllerAmount) {
            app.domRouter.manageAliases(controllerList);
            app.domRouter.replaceTagElementsInMainContainer();
        }
    }


    /**
     * wrapOnLoad wraps the prototyped onLoad function with a content load function.
     * it also sets the container variable.
     *
     * @param controllerClass - a class (Function) of a JavaScript controller object.
     * @param tagName - tag name
     */
    function wrapOnLoad(controllerClass, tagName) {
        let originOnLoad = controllerClass.prototype.onLoad || function () {
        };

        controllerClass.prototype.__tagName = tagName;

        controllerClass.prototype.onLoad = function () {
            let self = this;

            let superArgs = arguments;
            return app.contentRouter.loadFilesFromController(self, self.__tagName)
                .then(function () {
                    return originOnLoad.apply(self, superArgs);
                })
                .catch(function (err) {
                    console.error(err);
                });
        }
    }

    /**
     * wrapOnRemoveHandler adds the remove function to the controller.
     * The remove function calls the remove function of all children.
     * It removes the DOM from the HTML page and calls the onRemove
     * handler.
     *
     * If the onRemove function of one child controller or the controller
     * returns true method breaks.
     *
     *
     * @param controller - js controller instance
     */
    function wrapOnRemoveHandler(controller) {
        controller.remove = function () {
            let _childController = controller.childController;
            controller.childController = [];
            for (let i = 0; i < _childController.length; i++) {
                if (!_childController[i].remove()) {
                    return false;
                }
            }

            if (!controller.onRemove || !controller.onRemove()) {
                app.events.allOff(this);
                for (let l = 0; l < this.parentController.childController.length; l++) {
                    if (this.parentController.childController[l] === this) {
                        this.parentController.childController.splice(l, 1);
                    }
                }
                this.$container.remove();
                return true;

            }

            return false;
        };
    }

    /**
     * runControllerLoad Calls the onLoad function of the controller.
     * This function is called before the HTML is set to the page.
     * The parameter is a list of children of the tag and the registered tag.
     *
     * @param controller - js controller instance
     * @param $element - jQuery element of the registered tag
     * @return {Promise<*>} - return of the onLoad function
     */
    function runControllerLoad(controller, $element) {
        if (!controller.onLoad || controller[tagOnLoadDone]) {
            return window.utils.promiseDummyFactory();
        }

        controller[tagOnLoadDone] = true;
        let loadPromise = controller.onLoad($element.children(), $element);

        return loadPromise || window.utils.promiseDummyFactory();
    }


    /**
     * runControllerFillContent empties the registered tag and replaces it by the controller
     * content. It sets the CSS tags for the relation with the CSS files.
     *
     * @param controller - js controller instance
     * @param $element - jQuery element of the registered tag
     * @return {Promise}
     */
    function runControllerFillContent(controller, $element) {
        let content = controller.$content;
        if (content) {
            $element.empty();
            let tagName = $element.prop('tagName').toLowerCase();
            let tagNameList = tagName.split('_');
            for (let i = 0; i < tagNameList.length; i++) {
                $element.attr(tagNameList[i].toLowerCase(), '');
            }

            $element.append(content);
        }

        return new Promise(function (resolve) {
            app.domRouter.replaceAllTagElementsInContainer($element, controller, resolve);
        });
    }

    /**
     * runControllerShow first runs onLoad and fill content for all sub
     * controller. Only if all the sub controller are loaded the willShow
     * control flow function gets called.
     *
     * @param controller - js controller instance
     * @param $element - jQuery element of the registered tag
     * @return {Promise<*>} - return of the onLoad function
     */
    function runControllerShow(controller, $element) {
        return runControllerFillContent(controller, $element).then(function (args) {
            args = args || true;
            if (controller.willShow) {
                let loadPromiseOrContent = controller.willShow();
                if (loadPromiseOrContent instanceof Promise) {
                    return loadPromiseOrContent.then(function () {
                        return args;
                    });
                }
            }

            return args;
        });
    }

    /**
     * registerControllerList register all controllers. The list is a
     * list of the URLs of the controller. The list length defines the
     * number of controller. SDC waits until the number of registered
     * controller has the same as the list length. If isDebug is false
     * the controller need to be added handy at the HTM page
     *
     * @param list - URL list of controller
     * @param isdebug - Boolean true if you run debug mode
     */
    cm.registerControllerList = function (list, isdebug) {
        debug = isdebug;
        controllerAmount = list.length;

        if (isdebug) {
            app.contentRouter.downloadController(list);
        } else {
            checkIfAllControllerRegistered();
        }
    };

    /**
     * setDefaultSuperTags sets all super controller tags relaying
     * to the default super extensions.
     *
     * @param taglist - object tag list {tag: string[], super: string[], dom: jQuery}
     */
    cm.setDefaultSuperTags = function (taglist) {
        for (let i = 0; i < taglist.length; i++) {
            let tagItem = taglist[i];
            if (defaultSuperTags.hasOwnProperty(tagItem.tag)) {
                tagItem.super = tagItem.super.concat(defaultSuperTags[tagItem.tag]);
            }

            for (let l = 0; l < tagItem.super.length; l++) {
                if (defaultSuperTags.hasOwnProperty(tagItem.super[l])) {
                    tagItem.super = tagItem.super.concat(defaultSuperTags[tagItem.super[l]]);
                }
            }
        }
    };

    /**
     * Generates a function to extend a controller.
     * The retruned function allows simpy to set an default
     * super controller for each instance of the base controller.
     *
     * @param tag - base controller tag
     * @return {{extend: extend}} - function to default extend
     */
    function extendFunctionFactory(tag) {
        return {
            extend: function (superTags) {
                if (!(superTags instanceof Array)) {
                    superTags = [superTags]
                }

                for (let i = 0; i < superTags.length; ++i) {
                    superTags[i] = app.domRouter.makeTag(superTags[i]);
                }

                defaultSuperTags[tag] = superTags;
            }
        }
    }

    /**
     * registerGlobalController needs to be called for each global controller.
     * Call this function instead of registerController for global controller.
     * Each global has only one instance. It is note wise to use it with content.
     * Registered controller can be used in the HTML as a tag.
     *
     * @param tagCamelcase - tag name in camelcase
     * @param controller - a instance of a JavaScript controller object.
     * @return {{extend: extend}} - function to default extend
     */
    cm.registerGlobalController = function (tagCamelcase, controller) {
        let tag = app.domRouter.makeTag(tagCamelcase);
        app.domRouter.tagList.push(tag);

        wrapOnLoad(controller, tag);

        gcl[tagCamelcase] = globalControllerInstance[tag] = new controller();

        checkIfAllControllerRegistered();

        return extendFunctionFactory(tag);
    };

    /**
     * registerController needs to be called for each gloal controller.
     * Registered controller can be used in the HTML as a tag.
     *
     * @param tag - tag name in camelcase
     * @param controller - a class (Function) of a JavaScript controller object.
     * @return {{extend: extend}} - function to default extend
     *
     */
    cm.registerController = function (tag, controller) {
        tag = app.domRouter.makeTag(tag);
        app.domRouter.tagList.push(tag);

        wrapOnLoad(controller, tag);
        controllerList[tag] = controller;

        checkIfAllControllerRegistered();

        return extendFunctionFactory(tag);
    };

    /**
     * controllerFactory it either generates a controller or takes a globe instance
     * depending if the controller is registered as a global controller. It sets the
     * $container object to the jQuery representation of the tag.
     *
     * Remember Global controller can not have a super controller!
     *
     * @param parentController - Controller of the parent DOM
     * @param $element - The current DOM jQuery
     * @param tagName - the registered tag name of the current DOM
     * @param superTagNameList - tag names of super controller
     * @return {controller} -  new Controller
     */
    cm.controllerFactory = function (parentController, $element, tagName, superTagNameList) {
        if (globalControllerInstance[tagName]) {
            let controller = globalControllerInstance[tagName];
            setParentController(parentController, controller);
            controller.$container = $element;
            return controller;
        }

        return controllerFactoryInstance.apply(this, [parentController, $element, tagName, superTagNameList]);
    };

    /**
     * runControlFlowFunctions runs the control flow functions:
     * 1. onLoad()
     * 2. fill content
     * 3. willShow()
     * 4. afterShow()
     *
     * @param controller
     * @param $element
     * @param doneWithElementFunction
     */
    cm.runControlFlowFunctions = function (controller, $element, doneWithElementFunction) {
        runControllerLoad(controller, $element)
            .then(function () {
                return runControllerShow(controller, $element)
            })
            .then(function () {
                wrapOnRemoveHandler(controller);
                doneWithElementFunction(controller);
            });
    };

})(window.app || (window.app = {}));