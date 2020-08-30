(function (app) {
    "use strict";

    if(!app.VERSION) {
        app.VERSION = "V0.0"
    }
    /**
     * contentRouter - public contentRouter object.
     * @type {{
     *     setupEvents: function,
     *     downloadController: function,
     *     resetContentUrlOfController: function
     *     parseContentUrl: function
     *     setContentUrlPrefix: function
     *     loadFilesFromController: function
     * }}
     */
    let contentRouter = app.contentRouter = {};

    /**
     * List of Booleans if the are loaded files.
     * @type {{}}
     */
    let cssFilesLoaded = {};

    /**
     * List of HTML files.
     * @type {{}}
     */
    let htmlFiles = {};

    /**
     * The prefix for all content URLs of the controllers
     * @type {string}
     * @private
     */
    let _contentPrefix = '';

    /**
     * Reference to the HTML body.
     * @type {*|jQuery|HTMLElement}
     * @private
     */
    let _$body;

    /**
     * New content URs for specified controllers.
     * @type {{}}
     * @private
     */
    let _resetContentOfControllerList = {};

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

    /**
     * addCssFile generates a CSS style tag and adds it to the html body.
     * Manipulates the CSS rules by adding a tag name-related prefix.
     *
     * @param cssContent - loaded CSS file content
     * @param tag - a normalized tag-name as string.
     */
    function addCssFile(cssContent, tag) {
        let ruleRegexp = /^([^\{\n\d@]+)(\{[^\}]+\})/gm;
        cssContent = cssContent.replace(ruleRegexp, function (match, rule, content) {
            return "[" + tag + "] " + rule.split(',').join(",[" + tag + "] ") + content
        });

        getBody().append('<style rel="stylesheet">' + cssContent + '</style>');
    }

    /**
     * replacePlaceholderController fills the parameter of the content
     * url this function uses the tag parameter
     *
     * @param controller - controller object
     * @param url - the origin content URL
     * @param urlValues - values for the url placeholder. In same order!!
     * @returns {string} - the correct URL with prefix.
     */
    function replacePlaceholderController(controller, url, urlValues) {
        for (let key_idx in controller._urlParams) {
            if (controller._urlParams.hasOwnProperty(key_idx)) {
                let key = controller._urlParams[key_idx];
                let re = RegExp("%\\(" + key + "\\)\\w", "gm");
                url = url.replace(re, "" + urlValues.shift());
            }
        }

        return url;
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
        return (!/^[.#]/.test(domSelector) && /^[.#]/.test(eventType)) || eventType === 'this' || eventType.startsWith("$.");
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
     * bindEvent binds all HTML event handlers based on the events-object of
     * the controller for a given container.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to bind all controller events.
     * @param events - a jQuery object to bind all controller events.
     */
    function bindEvent(controller, $content, events) {
        for (let firstEventKey in events) {
            if (events.hasOwnProperty(firstEventKey)) {
                let eventList = events[firstEventKey];
                for (let secondEventKey in eventList) {
                    if (!secondEventKey.startsWith("_dh") && eventList.hasOwnProperty(secondEventKey)) {
                        let handler = eventList[secondEventKey];
                        let domSelector = secondEventKey;
                        let eventType = firstEventKey;
                        if (switchedDomSelectorAndEvent(secondEventKey, firstEventKey)) {
                            domSelector = firstEventKey;
                            eventType = secondEventKey;
                        }

                        if (domSelector === "$.window") {
                            eventList["_dh" + secondEventKey] = generateEventHandler(controller, handler);
                            $(window).on(eventType, eventList["_dh" + secondEventKey])
                        } else if (domSelector.startsWith("$.")) {
                            eventList["_dh" + secondEventKey] = generateEventHandler(controller, handler);
                            $(domSelector.substring(2)).on(eventType, eventList["_dh" + secondEventKey]);
                        } else if (domSelector === 'this') {
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
     * unbindEvent unbinds all HTML event handlers based on the events-object of
     * the controller for a given container.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to unbinds all controller events.
     * @param events - a jQuery object to unbinds all controller events.
     */
    function unbindEvent(controller, $content, events) {
        for (let firstEventKey in events) {
            if (events.hasOwnProperty(firstEventKey)) {
                let eventList = events[firstEventKey];
                for (let secondEventKey in eventList) {
                    if (!secondEventKey.startsWith("_dh") && eventList.hasOwnProperty(secondEventKey)) {
                        let domSelector = secondEventKey;
                        let eventType = firstEventKey;
                        if (switchedDomSelectorAndEvent(secondEventKey, firstEventKey)) {
                            domSelector = firstEventKey;
                            eventType = secondEventKey;
                        }

                        if (domSelector === "$.window") {
                            $(window).unbind(eventType, eventList["_dh" + secondEventKey]);
                        } else if (domSelector.startsWith("$.")) {
                            $(domSelector.substring(2)).unbind(eventType, eventList["_dh" + secondEventKey]);
                        } else if (domSelector === 'this') {
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
     * unbindAllControllerEvent unbinds all HTML event handlers based on the events-object of
     * the controller for a given container.
     *
     * @param controller - a instance of a JavaScript controller object.
     * @param $content - a jQuery object to unbind all controller events.
     */
    function unbindAllControllerEvent(controller, $content) {
        if (controller.events instanceof Array) {
            for (let i = 0; i < controller.events.length; i++) {
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
            for (let i = 0; i < controller.events.length; i++) {
                bindEvent(controller, $content, controller.events[i]);
            }

            return;
        }

        bindEvent(controller, $content, controller.events);
    }

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

        let $content = controller.$container;
        unbindAllControllerEvent(controller, $content);
        bindAllControllerEvent(controller, $content);
    };

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
            let $scripts = $('<div>' + data + '</div>').find('script');
            data = data.replace(/<script[^>]*>(.*?<\/script[^>]*>)?/gmi, '');

            $('body').append($scripts);
            if (!hardReload) {
                htmlFiles[tag] = data;
            }
            return data;
        }).catch(function (err) {
            console.error(err);
            return false;
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

        let cssFileLoadPromises = [];

        for (let i = 0; i < pathList.length; i++) {
            cssFileLoadPromises.push($.get(pathList[i]));
        }

        return Promise.all(cssFileLoadPromises).then(function (files) {
            for (let i = 0; i < files.length; i++) {
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
     * downloadController adds script-tags to the html-body. This should only be used in
     * a debug version of your Web-App.
     *
     * @param list - list of sources
     */
    contentRouter.downloadController = function (list) {
        for (let i = 0; i < list.length; i++) {
            getBody().append('<script src="' + list[i] + '?' + app.VERSION + '" type="text/javascript">');
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
            controller.contentUrl = contentRouter.parseContentUrl(controller, _resetContentOfControllerList[tag]);
        } else if (controller.contentUrl) {
            controller.contentUrl = contentRouter.parseContentUrl(controller, controller.contentUrl);
        }

        return Promise.all([
            loadHTMLFile(controller.contentUrl, tag, controller.contentRelaod),
            loadCSSFile(controller.cssUrls, tag)
        ]).then(function (results) {
            let htmlFile = results[0];
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
     * correct URL. Also parses the url parameter
     *
     * @param controller - controller object
     * @param url - the origin content URL
     * @returns {string} - the correct URL with prefix.
     */
    contentRouter.parseContentUrl = function (controller, url) {
        if (controller && !controller._urlParams) {
            let re = /%\(([^)]+)\)\w/gm;
            let matches;
            controller._urlParams = [];
            while ((matches = re.exec(url))) {
                controller._urlParams.push(matches[1]);
                controller.contentRelaod = true;
            }
        }

        if (controller._urlParams.length) {
            let params = app.paramManager.getUrlParam(controller, controller.$container);
            url = replacePlaceholderController(controller, url, params);
        }

        if (url.indexOf(_contentPrefix) === 0) {
            return url;
        }

        return _contentPrefix + url;
    };

})
(window.app || (window.app = {}));