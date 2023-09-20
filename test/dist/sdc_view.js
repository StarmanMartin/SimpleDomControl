"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.DATA_CONTROLLER_KEY = exports.CONTROLLER_CLASS = void 0;
exports.cleanCache = cleanCache;
exports.getController = getController;
exports.loadFilesFromController = loadFilesFromController;
exports.reloadHTMLController = reloadHTMLController;
exports.replaceTagElementsInContainer = replaceTagElementsInContainer;
exports.runControllerFillContent = runControllerFillContent;
var _sdc_controller = require("./sdc_controller.js");
var _sdc_params = require("./sdc_params.js");
var _sdc_main = require("./sdc_main.js");
var _sdc_events = require("./sdc_events");
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
var DATA_CONTROLLER_KEY = '_controller_';
exports.DATA_CONTROLLER_KEY = DATA_CONTROLLER_KEY;
var CONTROLLER_CLASS = '_sdc_controller_';
exports.CONTROLLER_CLASS = CONTROLLER_CLASS;
function cleanCache() {
  htmlFiles = {};
}
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
  var $children = $container.children();
  var emptyList = [];
  $children.each(function (_, element) {
    var $element = $(element);
    var tagName = $element.prop('tagName').toLowerCase().split('_');
    if ($.inArray(tagName[0], tagNameList) >= 0) {
      emptyList.push({
        tag: tagName[0],
        "super": tagName.splice(1) || [],
        dom: $element
      });
    } else {
      emptyList = emptyList.concat(findSdcTgs($element, tagNameList));
    }
  });
  return emptyList;
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
  for (var key_idx in controller._urlParams) {
    if (controller._urlParams.hasOwnProperty(key_idx)) {
      var key = controller._urlParams[key_idx];
      var re = RegExp("%\\(" + key + "\\)\\w", "gm");
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
    return Promise.resolve(htmlFiles[tag]);
  }
  args.VERSION = _sdc_main.app.VERSION;
  args._method = 'content';
  return $.get(path, args).then(function (data) {
    if (data.status === "redirect") {
      (0, _sdc_events.trigger)('onNavLink', data['url-link']);
      return "<sdc-error data-code='403'></sdc-error>";
    }
    if (!hardReload) {
      htmlFiles[tag] = data;
    }
    return data;
  })["catch"](function (err) {
    console.error(err);
    return err.responseText;
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
  return replaceTagElementsInContainer(_sdc_main.app.tagNames, $container, parentController);
}

/**
 * parseContentUrl uses the content URL prefix to marge the
 * correct URL. Also parses the url parameter
 *
 * @param {AbstractSDC} controller - controller object
 * @returns {string} - the correct URL with prefix.
 */
function parseContentUrl(controller) {
  var url = controller.contentUrl;
  if (controller && controller._urlParams.length === 0) {
    var re = /%\(([^)]+)\)\w/gm;
    var matches;
    controller._urlParams = [];
    while (matches = re.exec(url)) {
      controller._urlParams.push(matches[1]);
      controller.contentReload = true;
    }
  }
  var params = (0, _sdc_params.getUrlParam)(controller, controller.$container);
  if (controller._urlParams.length) {
    url = replacePlaceholderController(controller, url, params);
  }
  controller.parsedContentUrl = url;
  return {
    url: url,
    args: params[params.length - 1]
  };
}

/**
 *
 * @param {jquery} $elem
 * @return {AbstractSDC}
 */
function getController($elem) {
  if ($elem.hasClass(CONTROLLER_CLASS)) {
    return $elem.data("".concat(DATA_CONTROLLER_KEY));
  }
  return $elem.closest(".".concat(CONTROLLER_CLASS)).data("".concat(DATA_CONTROLLER_KEY));
}

/**
 * loadFilesFromController loads the content (HTML) of a
 * Controller. If you have an alternative content URL is registered, for this
 * controller the origin content URL is ignored.
 *
 * The content is saved as jQuery object to the controller.$content property of
 * the controller.
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 * @returns {Promise<jQuery>} - the promise waits to the files are loaded. it returns the jQuery object.
 */
function loadFilesFromController(controller) {
  var getElements = {
    args: {}
  };
  if (controller.contentUrl) {
    getElements = parseContentUrl(controller, controller.contentUrl);
    controller.contentUrl = getElements.url;
  }
  return Promise.all([loadHTMLFile(controller.contentUrl, getElements.args, controller._tagName, controller.contentReload)]).then(function (results) {
    var htmlFile = results[0];
    if (htmlFile) {
      return $(htmlFile);
    }
    return null;
  })["catch"](function (err) {
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
function reloadHTMLController(controller) {
  if (controller.contentUrl) {
    var getElements = parseContentUrl(controller, controller.contentUrl);
    controller.contentUrl = getElements.url;
    return loadHTMLFile(controller.contentUrl, getElements.args, controller._tagName, controller.contentReload);
  }
  return new Promise(function (resolve) {
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
  var controller = $element.data(DATA_CONTROLLER_KEY);
  if (controller) {
    return replaceAllTagElementsInContainer($element, controller);
  }
  controller = (0, _sdc_controller.controllerFactory)(parentController, $element, tagName, superTagNameList);
  $element.data(DATA_CONTROLLER_KEY, controller);
  $element.addClass(CONTROLLER_CLASS);
  return (0, _sdc_controller.runControlFlowFunctions)(controller, $element);
}

/**
 * runControllerFillContent empties the registered tag and replaces it by the controller
 * content. It sets the CSS tags for the relation with the CSS files.
 *
 * @param {AbstractSDC} controller - js controller instance
 * @param {jquery} $html - jQuery loaded content
 * @return {Promise}
 */
function runControllerFillContent(controller, $html) {
  if ($html && $html.length > 0) {
    controller.$container.empty();
    controller.$container.attr(controller._tagName, '');
    for (var mixinKey in controller._mixins) {
      controller.$container.attr(controller._mixins[mixinKey]._tagName, '');
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
function replaceTagElementsInContainer(tagList, $container, parentController) {
  return new Promise(function (resolve) {
    var tagDescriptionElements = findSdcTgs($container, tagList);
    var tagCount = tagDescriptionElements.length;
    if (tagCount === 0) {
      return resolve();
    }
    for (var elementIndex = 0; elementIndex < tagDescriptionElements.length; elementIndex++) {
      runReplaceTagElementsInContainer(tagDescriptionElements[elementIndex].dom, tagDescriptionElements[elementIndex].tag, tagDescriptionElements[elementIndex]["super"], parentController).then(function () {
        tagCount--;
        if (tagCount === 0) {
          return resolve();
        }
      });
    }
  });
}