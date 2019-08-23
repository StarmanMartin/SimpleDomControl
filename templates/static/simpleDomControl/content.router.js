(function (app) {

    /**
     * contentRouter - public contentRouter object.
     * @type {{}}
     */
    var contentRouter = app.contentRouter = {};

    /**
     * List of Booleans if the are loaded files.
     * @type {{}}
     */
    var cssFilesLoaded = {};

    /**
     * List of HTML files.
     * @type {{}}
     */
    var htmlFiles = {};

    /**
     * The prefix for all content URLs of the controllers
     * @type {string}
     * @private
     */
    var _contentPrefix = '';

    /**
     * Reference to the HTML body.
     * @type {*|jQuery|HTMLElement}
     * @private
     */
    var _$body;

    /**
     * New content URs for specified controllers.
     * @type {{}}
     * @private
     */
    var _resetContentOfControllerList = {};

    /**
     * downloadController adds script-tags to the html-body. This should only be used in
     * a debug version of your Web-App.
     *
     * @param list - list of sources
     */
    contentRouter.downloadController = function (list) {
        for (var i = 0; i < list.length; i++) {
            getBody().append('<script src="' + list[i] + '" type="text/javascript">')
        }
    };

    /**
     * resetContentUrlOfController enables to register an alternative content URL for controller.
     * This needs to be done before the controllers have been initializing.
     *
     * @param tag - a normalized tag-name as string
     * @param contentUrl - the new content url for the controller
     */
    contentRouter.resetContentUrlOfController = function (tag, contentUrl) {
        if (!contentUrl && _resetContentOfControllerList.hasOwnProperty(tag)) {
            delete _resetContentOfControllerList[tag];
            return;
        }
        _resetContentOfControllerList[tag] = contentUrl;
    };

    /**
     * loadFilesFromController loads the content (HTML) and the CSS files of a
     * Controller. If you have an alternative content URL is registered, for this
     * controller the origin content URL is ignored.
     *
     * The content is saved as jQuery object to the controller.$content property of
     * the controller.The CSS style tag(s) file will be added to the HTML file.
     * Each CSS rule is in the style-tag manipulated so that it only refers only
     * to children of the main controller tag.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param tag - a normalized tag-name as string.
     * @returns {Promise<jQuery>} - the promise waits to the files are loaded. it returns the jQuery object.
     */
    contentRouter.loadFilesFromController = function (controller, tag) {
        if (_resetContentOfControllerList.hasOwnProperty(tag)) {
            controller.contentUrl = contentRouter.parseContentUrl(_resetContentOfControllerList[tag]);
        } else if (controller.contentUrl) {
            controller.contentUrl = contentRouter.parseContentUrl(controller.contentUrl);
        }

        return Promise.all([
            loadHTMLFile(controller.contentUrl, tag, controller.contentRelaod),
            loadCSSFile(controller.cssUrls, tag)
        ]).then(function (results) {
            var htmlFile = results[0];
            if (htmlFile) {
                return (controller.$content = $(htmlFile));
            }

            return null;
        }).catch(function (err) {
            console.error("loadFiles-catch", err);
        });
    };

    /**
     * setContentUrlPrefix is a setter for the content URLs prefix
     *
     * @param prefix
     */
    contentRouter.setContentUrlPrefix = function (prefix) {
        _contentPrefix = prefix;
    };

    /**
     * parseContentUrl uses the content URL prefix to marge the
     * correct URL.
     *
     * @param url - the origin content URL
     * @returns {string} - the correct URL with prefix.
     */
    contentRouter.parseContentUrl = function (url) {
        if (url.indexOf(_contentPrefix) === 0) {
            return url;
        }

        return _contentPrefix + url;
    };

    /**
     * setupEvents first unbinds all HTML event handlers based on the events-object of
     * the controller. Then it rebinds all all HTML event handler using the events-object
     * of the controller.
     *
     * No action if the controler has no events object.
     *
     * @param controller - a instance of a JavaScript controller object.
     */
    contentRouter.setupEvents = function (controller) {
        if (!controller.events) {
            return true;
        }

        var $content = controller.$container;
        unbindAllControllerEvent(controller, $content);
        bindAllControllerEvent(controller, $content);
    };

    /**
     * unbindAllControllerEvent unbinds all HTML event handlers based on the events-object of
     * the controller for a given container.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to unbind all controller events.
     */
    function unbindAllControllerEvent(controller, $content) {
        if (controller.events instanceof Array) {
            for (var i = 0; i < controller.events.length; i++) {
                unbindEvent(controller, $content, controller.events[i]);
            }

            return;
        }

        unbindEvent(controller, $content, controller.events);
    }

    /**
     * bindAllControllerEvent binds all HTML event handlers based on the events-object of
     * the controller for a given container. This function iterates over the super controller
     * events.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to bind all controller events.
     */
    function bindAllControllerEvent(controller, $content) {
        if (controller.events instanceof Array) {
            for (var i = 0; i < controller.events.length; i++) {
                bindEvent(controller, $content, controller.events[i]);
            }

            return;
        }

        bindEvent(controller, $content, controller.events);
    }

    /**
     * bindEvent binds all HTML event handlers based on the events-object of
     * the controller for a given container.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to bind all controller events.
     * @param events - a jQuery object to bind all controller events.
     */
    function bindEvent(controller, $content, events) {
        for (var firstEventKey in events) {
            if (events.hasOwnProperty(firstEventKey)) {
                var eventList = events[firstEventKey];
                for (var secondEventKey in eventList) {
                    if (eventList.hasOwnProperty(secondEventKey)) {
                        var handler = eventList[secondEventKey];
                        var domSelector = secondEventKey;
                        var eventType = firstEventKey;
                        if (switchedDomSelectorAndEvent(secondEventKey, firstEventKey)) {
                            domSelector = firstEventKey;
                            eventType = secondEventKey;
                        }

                        if (domSelector === 'this') {
                            $content.on(eventType, generateEventHandler(controller, handler));
                        } else {
                            $content.find(domSelector).on(eventType, generateEventHandler(controller, handler));
                        }
                    }
                }
            }
        }
    }

    /**
     * switchedDomSelectorAndEvent if string is a CSS class or CSS id selector or an event.
     * Based on this it decides if domSelector is the selector or eventType is the selector.
     * If domSelector is the selector it says true.
     *
     * @param domSelector - selector or event string
     * @param eventType - selector or event string
     * @returns {boolean|*} - If the domSelector is a selector and not the eventType
     */
    function switchedDomSelectorAndEvent(domSelector, eventType) {
        return (!/^[.#]/.test(domSelector) && /^[.#]/.test(eventType)) || eventType === 'this';
    }

    /**
     * generateEventHandler wraps the event handler and binds this to the the controller.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param handler - origin handler function
     * @returns {Function} - wrapped handler function
     */
    function generateEventHandler(controller, handler) {
        return function (ev) {
            handler.call(controller, this, ev);
        }
    }

    /**
     * unbindEvent unbinds all HTML event handlers based on the events-object of
     * the controller for a given container.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to unbinds all controller events.
     * @param events - a jQuery object to unbinds all controller events.
     */
    function unbindEvent(controller, $content, events) {
        for (var firstEventKey in events) {
            if (events.hasOwnProperty(firstEventKey)) {
                var eventList = events[firstEventKey];
                for (var secondEventKey in eventList) {
                    if (eventList.hasOwnProperty(secondEventKey)) {
                        var domSelector = secondEventKey;
                        var eventType = firstEventKey;
                        if (switchedDomSelectorAndEvent(secondEventKey, firstEventKey)) {
                            domSelector = firstEventKey;
                            eventType = secondEventKey;
                        }

                        if (domSelector === 'this') {
                            $content.unbind(eventType);
                        } else {
                            $content.find(domSelector).unbind(eventType);
                        }
                    }
                }
            }
        }
    }

    /**
     * loadHTMLFile loads the HTML content file from the server via ajax request.
     *
     * If the HTML file is loaded already the function takes no action.
     *
     * @param path - a content URL from the controller.
     * @param tag - a normalized tag-name as string.
     * @param hardReload - true if the file has to be reloaded every time.
     * @returns {Promise<Boolean>} - waits for the file to be loaded.
     */
    function loadHTMLFile(path, tag, hardReload) {
        if (!path) {
            return Promise.resolve(false);
        } else if (htmlFiles[tag]) {
            return Promise.resolve(htmlFiles[tag])
        }

        return $.get(path).then(function (data) {
            var $scripts = $('<div>' + data + '</div>').find('script');
            data = data.replace(/<script[^>]*>(.*?<\/script[^>]*>)?/gmi, '');

            $('body').append($scripts);
            if (!hardReload) {
                htmlFiles[tag] = data;
            }
            return data;
        }).catch(function (err) {
            console.error(err);
            return false
        });
    }

    /**
     * loadCSSFile loads the CSS files from the server via ajax request.
     *  Manipulates the CSS rules by adding a tag name-related prefix.
     *  Adds a style tag to the HTML body.
     *
     * If the CSS file is loaded already the function takes no action.
     *
     * @param pathList - a list of CSS files from the controller.
     * @param tag - a normalized tag-name as string.
     * @returns {Promise<Boolean>} - waits for the files to be loaded.
     */
    function loadCSSFile(pathList, tag) {
        if (!pathList || pathList.length === 0) {
            return Promise.resolve(false);
        } else if (cssFilesLoaded[tag]) {
            return Promise.resolve(cssFilesLoaded[tag])
        }

        cssFilesLoaded[tag] = true;

        if (typeof pathList === "string") {
            pathList = [pathList]
        }

        var cssFileLoadPromises = [];

        for (var i = 0; i < pathList.length; i++) {
            cssFileLoadPromises.push($.get(pathList[i]))
        }

        return Promise.all(cssFileLoadPromises).then(function (files) {
            for (var i = 0; i < files.length; i++) {
                addCssFile(files[i], tag)
            }

            return true;
        }).catch(function (err) {
            cssFilesLoaded[tag] = false;
            console.error(err);
            return false
        });
    }

    /**
     * addCssFile generates a CSS style tag and adds it to the html body.
     * Manipulates the CSS rules by adding a tag name-related prefix.
     *
     * @param cssContent - loaded CSS file content
     * @param tag - a normalized tag-name as string.
     */
    function addCssFile(cssContent, tag) {
        var ruleRegexp = /^([^\{\n\d@]+)(\{[^\}]+\})/gm;
        cssContent = cssContent.replace(ruleRegexp, function (match, rule, content) {
            return "[" + tag + "] " + rule.split(',').join(",[" + tag + "] ") + content
        });

        getBody().append('<style rel="stylesheet">' + cssContent + '</style>');
    }

    /**
     * getBody returns the $body jQuery object.
     *
     * @returns {*|jQuery|HTMLElement} - body reference.
     */
    function getBody() {
        if (!_$body) {
            _$body = $('body');
        }

        return _$body;
    }

})(window.app || (window.app = {}));