import {getBody} from './sdc_utils.js'
import {controllerFactory,runControlFlowFunctions} from "./sdc_controller.js";
import {getUrlParam} from "./sdc_params.js";
import {app} from "./sdc_main.js";

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

export const DATA_CONTROLLER_KEY = '_controller_';
export const CONTROLLER_CLASS = '_sdc_controller_';

/**
 * findSdcTgs Finds all registered tags in a container. But it ignores
 * registered tags in registered tags. It collects all those
 * doms and returns a list of objects containing also the tag name the dom and the tag
 * names of the super controller
 *
 * @param {jquery} $container - jQuery container
 * @param {Array<string>} tagNameList - a string list with tag names.
 * @return {Array} - a array of objects with all register tags found
 */
function findSdcTgs($container, tagNameList) {
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
            emptyList = emptyList.concat(findSdcTgs($element, tagNameList))
        }
    });

    return emptyList;
}

/**
 * addCssFile generates a CSS style tag and adds it to the html body.
 * Manipulates the CSS rules by adding a tag name-related prefix.
 *
 * @param cssContent - loaded CSS file content
 * @param tag - a normalized tag-name as string.
 */
function addCssFile(cssContent, tag) {
    let ruleRegexp = /^([^{\n@]+)({[^}]+})/gm;
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
 * loadHTMLFile loads the HTML content file from the server via ajax request.
 *
 * If the HTML file is loaded already the function takes no action.
 *
 * @param path - a content URL from the controller.
 * @param {object} args - get args.
 * @param tag - a normalized tag-name as string.
 * @param hardReload - true if the file has to be reloaded every time.
 * @returns {Promise<Boolean>} - waits for the file to be loaded.
 */
function loadHTMLFile(path, args, tag, hardReload) {
    if (!path) {
        return Promise.resolve(false);
    } else if (htmlFiles[tag]) {
        return Promise.resolve(htmlFiles[tag])
    }

    args.VERSION = app.VERSION;
    args._method = 'content';


    return $.get(path, args).then(function (data) {
        if (!hardReload) {
            htmlFiles[tag] = data;
        }

        return data;
    }).catch(function (err) {
        console.log(err);
        return err.responseText;
    });
}

/**
 * loadCSSFile loads the CSS files from the server via ajax request.
 *  Manipulates the CSS rules by adding a tag name-related prefix.
 *  Adds a style tag to the HTML body.
 *
 * If the CSS file is loaded already the function takes no action.
 *
 * @param {Array<string>|string} pathList - a list of CSS files from the controller.
 * @param {string} tag - a normalized tag-name as string.
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
        if (pathList[i].indexOf('?') === -1) {
            pathList[i] += '?' + app.VERSION;
        }
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
 * replaceAllTagElementsInContainer replaces all registered tags by the controller.
 * In this step the life-cycle starts.
 *
 * @param {jquery} $container - given container
 * @param {AbstractSDC} parentController - parent contoller surrounded the container
 */
function replaceAllTagElementsInContainer($container, parentController) {
    parentController = parentController || $container.data(DATA_CONTROLLER_KEY);
    return replaceTagElementsInContainer(app.tagNames, $container, parentController);
}

/**
 * parseContentUrl uses the content URL prefix to marge the
 * correct URL. Also parses the url parameter
 *
 * @param {AbstractSDC} controller - controller object
 * @returns {string} - the correct URL with prefix.
 */
function parseContentUrl(controller) {
    let url = controller.contentUrl;
    if (controller && controller._urlParams.length === 0) {
        let re = /%\(([^)]+)\)\w/gm;
        let matches;
        controller._urlParams = [];
        while ((matches = re.exec(url))) {
            controller._urlParams.push(matches[1]);
            controller.contentReload = true;
        }
    }

    let params = getUrlParam(controller, controller.$container);
    if (controller._urlParams.length) {
        url = replacePlaceholderController(controller, url, params);
    }

    controller.parsedContentUrl = url;

    return {url:url, args:params[params.length-1]};
}

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
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 * @returns {Promise<jQuery>} - the promise waits to the files are loaded. it returns the jQuery object.
 */
export function loadFilesFromController(controller) {
    let getElements = {args:{}};
    if (controller.contentUrl) {
        getElements = parseContentUrl(controller, controller.contentUrl);
        controller.contentUrl = getElements.url;
    }

    return Promise.all([
        loadHTMLFile(controller.contentUrl, getElements.args, controller._tagName, controller.contentReload),
        loadCSSFile(controller.cssUrls, controller._tagName)
    ]).then(function (results) {
        let htmlFile = results[0];
        if (htmlFile) {
            return $(htmlFile);
        }

        return null;
    }).catch(function (err) {
        console.log(9999);
        console.error("loadFiles-catch", err);
    });
}

/**
 * reloadHTMLController loads the content (HTML) of a
 * Controller. If you have an alternative content URL is registered, for this
 * controller the origin content URL is ignored.
 *
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 *
 * @returns {Promise<jQuery>} - the promise waits to the files are loaded. it returns the jQuery object.
 */
export function reloadHTMLController(controller) {
    if (controller.contentUrl) {
        let getElements = parseContentUrl(controller, controller.contentUrl);
        controller.contentUrl = getElements.url;
        return loadHTMLFile(controller.contentUrl, getElements.args, controller._tagName, controller.contentReload);
    }

    return new Promise(resolve => {
        resolve($());
    });
}

/**
 *
 * @param {jquery} $element
 * @param {string} tagName
 * @param {Array<string>} superTagNameList
 * @param {AbstractSDC} parentController
 * @returns {boolean}
 */
function runReplaceTagElementsInContainer($element, tagName, superTagNameList, parentController) {
    let controller = $element.data(DATA_CONTROLLER_KEY);
    if (controller) {
        return replaceAllTagElementsInContainer($element, controller);
    }

    controller = controllerFactory(parentController, $element, tagName, superTagNameList);
    $element.data(DATA_CONTROLLER_KEY, controller);
    $element.addClass(CONTROLLER_CLASS);
    return runControlFlowFunctions(controller, $element);
}



/**
 * runControllerFillContent empties the registered tag and replaces it by the controller
 * content. It sets the CSS tags for the relation with the CSS files.
 *
 * @param {AbstractSDC} controller - js controller instance
 * @param {jquery} $html - jQuery loaded content
 * @return {Promise}
 */
export function runControllerFillContent(controller, $html) {
    if ($html && $html.length > 0) {
        controller.$container.empty();
        let tagName = controller.$container.prop('tagName').toLowerCase();
        let tagNameList = tagName.split('_');
        for (let i = 0; i < tagNameList.length; i++) {
            controller.$container.attr(tagNameList[i].toLowerCase(), '');
        }

        controller.$container.append($html);
    }

    return replaceAllTagElementsInContainer(controller.$container, controller);
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
 */
export function replaceTagElementsInContainer(tagList, $container, parentController) {
    return new Promise((resolve) => {

        let tagDescriptionElements = findSdcTgs($container, tagList);
        let tagCount = tagDescriptionElements.length;

        if (tagCount === 0) {
            return resolve();
        }

        for (let elementIndex = 0; elementIndex < tagDescriptionElements.length; elementIndex++) {
            runReplaceTagElementsInContainer(tagDescriptionElements[elementIndex].dom,
                tagDescriptionElements[elementIndex].tag,
                tagDescriptionElements[elementIndex].super,
                parentController).then(() => {
                tagCount--;
                if (tagCount === 0) {
                    return resolve();
                }
            });
        }
    });
}