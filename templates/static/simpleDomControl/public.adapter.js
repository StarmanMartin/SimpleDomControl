function RunPublic(app) {

    /**
     * resetContentUrlOfController enables to register an alternative content URL for controller.
     * This needs to be done before the controllers have been initializing.
     *
     * @param tag - a normalized tag-name as string
     * @param contentUrl - the new content url for the controller
     * @return  as - (function(newTag:string)) to register controller with new contant with an alterntive tag name
     *
     */
    app.resetContentUrlOfController = function (tag, contentUrl) {
        tag = app.domRouter.makeTag(tag);
        app.contentRouter.resetContentUrlOfController(tag, contentUrl);
        return {
            /**
             * register an alias for an controller
             *
             * @param newTag - new tag (alias) as string
             */
            as: function(newTag){
                newTag = app.domRouter.makeTag(newTag);
                app.contentRouter.resetContentUrlOfController(tag);
                app.contentRouter.resetContentUrlOfController(newTag, contentUrl);
                app.domRouter.registerAlias(tag, newTag);
            }
        }
    };

    /**
     * setContentUrlPrefix is a setter for the content URLs prefix
     *
     * @param prefix
     */
    app.setContentUrlPrefix = function (prefix) {
        app.contentRouter.setContentUrlPrefix(prefix);
    };


    /**
     * parseContentUrl uses the content URL prefix to marge the
     * correct URL.
     *
     * @param url - the origin content URL
     * @returns {string} - the correct URL with prefix.
     */
    app.parseContentUrl = function (url) {
        return app.contentRouter.parseContentUrl(url);
    };

    /**
     * setMainContainer set the main container where  all the
     * magic happens.
     *
     * @param $container - jquery object
     */
    app.setMainContainer = function ($container) {
        app.domRouter.$mainContainer = $container;
    };

    /**
     * getControllerOfElement simply returns the controller bound to the the element.
     * It returns the controller if there is one. Else it return null.
     *
     * @param $container - jQuery container with a controller
     * @return {Object} - returns the controller
     */
    app.getControllerOfElement = function ($container) {
        return app.domRouter.getControllerOfElement($container);
    };

    /**
     * onComponentLoad adds a handler function for on all components loaded
     *
     * @param handler - Function
     */
    app.onComponentLoad = function (handler) {
        app.controllerManager.onComponentLoadHandlerList.push(handler);
    };

    /**
     * reloadEvents reloads all events of a controller based on the
     * controllers events object.
     *
     * @param controller - js controller instance (after willShow)
     */
    app.reloadEvents = function (controller) {

        function _rec_reloadEvents(inner_controller) {
            app.contentRouter.setupEvents(inner_controller);
            for (var i = 0; i < inner_controller.childController.length; i++) {
                _rec_reloadEvents(inner_controller.childController[i]);
            }
        }

        _rec_reloadEvents(controller);

        app.events.trigger('onReloadEvents', controller);
    };

    /**
     * refreshContainer reloads and replaces all tags in the controllers container.
     * Inits the sub controllers and starts the life cycle.
     *
     * It reloads all events of a controller based on the
     * controllers events object.
     *
     * @param $container - js controller instance (after willShow)
     * @param controller - js controller instance (after willShow)
     * @return {Promise<>} Waits until done. No parameter
     */
    app.refreshContainer = function ($container, controller) {
        return new Promise(function (resolve) {
            app.domRouter.replaceAllTagElementsInContainer($container, controller, function () {
                if (controller) {
                    app.reloadEvents(controller);
                    controller.afterShow && controller.afterShow();
                    var onComponentLoadHandlerList = app.controllerManager.onComponentLoadHandlerList;
                    for (var i = 0; i < onComponentLoadHandlerList.length; ++i) {
                        onComponentLoadHandlerList[i]();
                    }
                }

                resolve();
            });
        });
    };

    /**
     * refreshController reloads and replaces all tags in the controllers container.
     * Inits the sub controllers and starts the life cycle.
     *
     * It reloads all events of a controller based on the
     * controllers events object.
     *
     * @param controller
     * @return {Promise}
     */
    app.refreshController = function (controller) {
        return app.refreshContainer(controller.$content, controller);
    };

    /**
     * splitParamsListOfDom splits the parameter from the jQuery element. It takes
     * the values of the parameter from the controller instance. The parameter-
     * list needs to be listed from a HTML data field. The name of the data field
     * is the same as the parameter dataKey.
     *
     * Rules for parameter ->
     *  separated by space
     *  normal text is reference of property of controller
     *  in single quotes -> string
     *  numbers -> int or float
     *
     * @param $element - jQuery DOM
     * @param dataKey - data tag name z.B. if dataKey = 'sammple-key' -> <a data-sample-key="'sample'"></a>
     * @return {*}
     */
    app.splitParamsListOfDom = function ($element, dataKey) {
        var dataResults = $element.data(dataKey);
        if(!dataResults) {
            return [];
        }

        return app.paramManager.splitParamList(dataResults);
    };

    /**
     * safeRemove removes a dom and deletes all child controller safely.
     *
     * @param $dom - jQuery Dom
     */
    app.safeRemove = function($dom) {
        app.domRouter.safeRemove($dom);
    };

    /**
     * safeEmpty removes all content of a dom
     * and deletes all child controller safely.
     *
     * @param $dom - jQuery DOM container to be emptyed
     */
    app.safeEmpty = function ($dom) {
        var $children = $dom.children();
        $children.each(function (_, element) {
            var $element = $(element);
            app.safeRemove($element);
        });

        return $dom;
    };

    /**
     * safeReplace removes the dom
     * and deletes all child controller safely.
     * After it replaces it by the new DOM
     *
     * @param $dom - jQuery DOM container to be emptyed
     * @param $newDom - jQuery DOM container to be emptyed
     */
    app.safeReplace = function ($dom, $newDom) {
        $newDom.insertBefore($dom);
        app.safeRemove($dom);

        return $newDom;
    };

    /**
     * parseParams parses the parameter defined in a list. It takes
     * the values of the parameter from the controller instance.
     * The name of the data field is the same as the parameter dataKey.
     *
     * Rules for parameter ->
     *  separated by space
     *  normal text is reference of property of controller
     *  in single quotes -> string
     *  numbers -> int or float
     *
     * @param controller - js controller instance
     * @param listConstructorParams - jQuery DOM
     * @return {*}
     */
    app.parseParams = function (controller, listConstructorParams) {
        return app.paramManager.parse(controller, listConstructorParams);
    };

    app.registerControllerList = app.controllerManager.registerControllerList;
    app.registerGlobalController = app.controllerManager.registerGlobalController;
    app.registerController = app.controllerManager.registerController;

    app.GlobalController = app.controllerManager.GlobalController;
}



(function (app) {

    function checkElements() {
        if (!app.contentRouter ||
            !app.events ||
            !app.controllerManager ||
            !app.domRouter ||
            !app.paramManager ||
            !app.simpleDomInit) {

            setTimeout(checkElements, 10);
            return;
        }

        RunPublic(app);
        app.simpleDomInit(app);
    }

    checkElements();

})(window.app || (window.app = {}));