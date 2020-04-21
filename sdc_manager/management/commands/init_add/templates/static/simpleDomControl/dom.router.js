(function (app) {
    "use strict";


    /**
     * tagCamelCaseToLine finds upper case letters
     * @type {RegExp}
     */
    const tagCamelCaseToLine1 = /(.)([A-Z])([a-z]+)/g;
    const tagCamelCaseToLine2 = /([a-z0-9])([A-Z])/g;

    /**
     * The public domRouter objects
     * @type {{
     *     makeTag: function,
     *     registerAlias: function,
     *      manageAliases: function,
     *      replaceAllTagElementsInContainer: function,
     *      getControllerOfElement: function,
     *      replaceTagElementsInMainContainer: function,
     *     safeRemove: function,
     *     aliasList: {},
     *     tagList: [],
     *     $mainContainer: object,
     *     dataControllerName: string
     *
     * }}
     */
    let domRouter = app.domRouter = {};

    /**
     * $mainContainer is the jQuery object. It is a super container.
     * By default is is the body element.
     * @type {{}}
     */
    domRouter.$mainContainer = $('body');

    /**
     * tagList is a list with all possible tags registered.
     * @type {Array}
     */
    domRouter.tagList = [];

    /**
     * aliasList is a list with tags registered with a second Name.
     * @type {Object}
     */
    domRouter.aliasList = {};

    /**
     * Data tag name for controller instance connection.
     * @type {string}
     */
    let dataControllerName = domRouter.dataControllerName = '_simple-dom-control';

    /**
     * jqueryFindExtension Finds all registered tags in a container. But it ignores
     * registered tags in registered tags. It collects all those
     * doms and returns a list of objects containing also the tag name the dom and the tag
     * names of the super controller
     *
     * @param $container - jQuery container
     * @param tagNameList - a string list with tag names.
     * @return {Array} - a array of objects with all register tags found
     */
    function jqueryFindExtension($container, tagNameList) {
        if (!$container) {
            return [];
        }
        let $children = $container.children();
        let emptyList = [];
        $children.each(function (_, element) {
            let $element = $(element);
            let tagName = $element.prop('tagName').toLowerCase().split('_');
            if ($.inArray(tagName[0], tagNameList) >= 0) {
                emptyList.push({
                    tag: tagName[0],
                    super: tagName.splice(1) || [],
                    dom: $element
                });

            } else {
                emptyList = emptyList.concat(jqueryFindExtension($element, tagNameList))
            }
        });

        return emptyList;
    }

    /**
     * replaceTagElementsInContainer Finds all registered tags in a container. But it ignores
     * registered tags in registered tags. For each registered tag it loads the content.
     * Afterwards it starts the life cycle of the controller. I the next step it starts the
     * procedure for the child elements of the controller tag.
     *
     * @param tagList - list of all registered tags
     * @param $container - jQuery container to find the tags
     * @param parentController - controller in surrounding
     * @param cb - callback function
     */
    function replaceTagElementsInContainer(tagList, $container, parentController, cb) {
        let tagDescriptionElements = jqueryFindExtension($container, tagList);
        app.controllerManager.setDefaultSuperTags(tagDescriptionElements);
        let tagCount = tagDescriptionElements.length;

        if (tagCount === 0 && typeof cb === 'function') {
            return cb();
        }

        let doneWithElementFunction = function (controller) {
            app.contentRouter.setupEvents(controller);
            controller.afterShow && controller.afterShow();
            tagCount--;
            if (tagCount === 0 && cb && typeof cb === 'function') {
                cb();
            }
        };

        function runReplaceTagElementsInContainer($element, tagName, superTagNameList) {
            let controller = $element.data(dataControllerName);
            if (controller) {
                domRouter.replaceAllTagElementsInContainer($element, controller, function () {
                    doneWithElementFunction(controller)
                });
                return;
            }

            controller = app.controllerManager.controllerFactory(parentController, $element, tagName, superTagNameList);
            $element.data(domRouter.dataControllerName, controller);
            app.controllerManager.runControlFlowFunctions(controller, $element, doneWithElementFunction);

        }

        for (let elementIndex = 0; elementIndex < tagDescriptionElements.length; elementIndex++) {
            runReplaceTagElementsInContainer(tagDescriptionElements[elementIndex].dom, tagDescriptionElements[elementIndex].tag, tagDescriptionElements[elementIndex].super);
        }
    }

    /**
     * makeTag replaces camel-case to dashed string.
     *
     * @param tag - tag as string
     * @returns {String} - as dash connected tag name
     */
    domRouter.makeTag = function (tag) {
        tag = tag.replace(tagCamelCaseToLine1, function (match, prefix, letter, sufix) {
            return prefix + '-' + letter.toLowerCase() + sufix;
        });

        tag = tag.replace(tagCamelCaseToLine2, function (match, prefix, letter) {
            return prefix + '-' + letter.toLowerCase();
        });

        return tag.toLocaleLowerCase();
    };

    /**
     * register an alias for an controller
     *
     * @param tag - tag as string
     * @param newTag - new tag (alias) as string
     */
    domRouter.registerAlias = function (tag, newTag) {
        domRouter.aliasList[newTag] = tag;
    };
    /**
     * register an alias for an controller
     *
     */
    domRouter.manageAliases = function (controllerList) {
        for (let newTag in domRouter.aliasList) {
            let oldTag = domRouter.aliasList[newTag];
            if (domRouter.aliasList.hasOwnProperty(newTag) && controllerList.hasOwnProperty(oldTag)) {
                domRouter.tagList.push(newTag);
                controllerList[newTag] = controllerList[oldTag];
                controllerList[newTag].prototype.__tagName = newTag;
            }
        }
    };

    /**
     * replaceAllTagElementsInContainer replaces all registered tags by the controller.
     * In this step the life-cycle starts.
     *
     * @param $container - given container
     * @param parentController - parent contoller surrounded the container
     * @param cb - callback function
     */
    domRouter.replaceAllTagElementsInContainer = function ($container, parentController, cb) {
        parentController = parentController || $container.data(dataControllerName);
        replaceTagElementsInContainer(domRouter.tagList, $container, parentController, function () {
            if (cb) {
                cb();
            }
        });
    };

    /**
     * getControllerOfElement simply returns the controller bound to the the element.
     * It returns the controller if there is one. Else it return null.
     *
     * @param $container - jQuery container with a controller
     * @return {Object} - returns the controller
     */
    domRouter.getControllerOfElement = function ($container) {
        return $container.data(domRouter.dataControllerName);
    };

    /**
     * replaceTagElementsInMainContainer replaces all registered tags by the controller.
     * In this step the life-cycle starts. Runs all component on Load handler after done.
     */
    domRouter.replaceTagElementsInMainContainer = function () {
        domRouter.replaceAllTagElementsInContainer(domRouter.$mainContainer, null, function () {
            for (let i = 0; i < app.controllerManager.onComponentLoadHandlerList.length; ++i) {
                app.controllerManager.onComponentLoadHandlerList[i]()
            }
        });
    };

    /**
     * safeRemove removes a dom and deletes all child controller safely.
     *
     * @param $dom - jQuery Dom
     */
    domRouter.safeRemove = function ($dom) {
        let allChildren = jqueryFindExtension($dom, domRouter.tagList);
        for (let i = 0; i < allChildren.length; i++) {
            domRouter.getControllerOfElement(allChildren[i].dom).remove();
        }

        let dc = domRouter.getControllerOfElement($dom);
        if(dc) {
            dc.remove();
        }

        $dom.remove();
    };
})(window.app || (window.app = {}));