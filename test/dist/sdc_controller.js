"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.Global = void 0;
exports.controllerFactory = controllerFactory;
exports.controllerList = void 0;
exports.runControlFlowFunctions = runControlFlowFunctions;
var _sdc_utils = require("./sdc_utils.js");
var _sdc_view = require("./sdc_view.js");
var _sdc_params = require("./sdc_params.js");
function _createForOfIteratorHelper(o, allowArrayLike) { var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"]; if (!it) { if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") { if (it) o = it; var i = 0; var F = function F() {}; return { s: F, n: function n() { if (i >= o.length) return { done: true }; return { done: false, value: o[i++] }; }, e: function e(_e) { throw _e; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var normalCompletion = true, didErr = false, err; return { s: function s() { it = it.call(o); }, n: function n() { var step = it.next(); normalCompletion = step.done; return step; }, e: function e(_e2) { didErr = true; err = _e2; }, f: function f() { try { if (!normalCompletion && it["return"] != null) it["return"](); } finally { if (didErr) throw err; } } }; }
function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }
function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i]; return arr2; }
var Global = {};
exports.Global = Global;
var controllerList = {};
exports.controllerList = controllerList;
function prepareMixins(superTagNameList, tagName) {
  superTagNameList = superTagNameList.concat(controllerList[tagName][1]);
  superTagNameList = superTagNameList.filter(function (value, index, self) {
    return self.indexOf(value) === index;
  });
  var hasAdded = true;
  while (hasAdded) {
    hasAdded = false;
    var _iterator = _createForOfIteratorHelper(superTagNameList),
      _step;
    try {
      for (_iterator.s(); !(_step = _iterator.n()).done;) {
        var tag = _step.value;
        var _iterator2 = _createForOfIteratorHelper(controllerList[tag][1]),
          _step2;
        try {
          for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
            var newTag = _step2.value;
            if (!superTagNameList.includes(newTag)) {
              superTagNameList.push(newTag);
              hasAdded = true;
            }
          }
        } catch (err) {
          _iterator2.e(err);
        } finally {
          _iterator2.f();
        }
      }
    } catch (err) {
      _iterator.e(err);
    } finally {
      _iterator.f();
    }
  }
  return superTagNameList;
}

/**
 * setParentController sets the parent controller as property: 'parentController'
 * to the child controller. Also it adds the child controller to the property list:
 * 'parentController' to the parent controller
 *
 * @param {AbstractSDC} parentController - js controller instance, controller of the parent DOM of the controllers DOM
 * @param {AbstractSDC} controller - js controller instance
 * @return {AbstractSDC} - parentController
 */
function setParentController(parentController, controller) {
  if (parentController) {
    var controllerName = (0, _sdc_utils.tagNameToCamelCase)(controller._tagName);
    if (!parentController._childController[controllerName]) {
      parentController._childController[controllerName] = [];
    }
    parentController._childController[controllerName].push(controller);
  }
  return controller._parentController = parentController;
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
 * @param {AbstractSDC} parentController - Controller of the parent DOM
 * @param {jquery} $element - The current DOM jQuery
 * @param {string} tagName - the registered tag name of the current DOM
 * @param {string} superTagNameList - tag names of super controller
 * @return {AbstractSDC} -  new Controller
 */
function controllerFactoryInstance(parentController, $element, tagName, superTagNameList) {
  var mixinControllerClass = [];
  superTagNameList = prepareMixins(superTagNameList, tagName);
  var _iterator3 = _createForOfIteratorHelper(superTagNameList),
    _step3;
  try {
    for (_iterator3.s(); !(_step3 = _iterator3.n()).done;) {
      var superTagName = _step3.value;
      mixinControllerClass.push(controllerList[superTagName][0]);
    }
  } catch (err) {
    _iterator3.e(err);
  } finally {
    _iterator3.f();
  }
  var controllerClass = controllerList[tagName][0];
  var controller = new (_sdc_utils.agileAggregation.apply(void 0, [controllerClass].concat(mixinControllerClass)))();
  controller._tagName = tagName;
  setParentController(parentController, controller);
  controller.$container = $element;
  (0, _sdc_params.runOnInitWithParameter)($element, controller);
  return controller;
}

/**
 * controllerFactory it either generates a controller or takes a globe instance
 * depending if the controller is registered as a global controller. It sets the
 * $container object to the jQuery representation of the tag.
 *
 * Remember Global controller can not have a super controller!
 *
 * @param {AbstractSDC} parentController - Controller of the parent DOM
 * @param {jquery} $element - The current DOM jQuery
 * @param {string} tagName - the registered tag name of the current DOM
 * @param {string} superTagNameList - tag names of super controller
 * @return {AbstractSDC} -  new Controller
 */
function controllerFactory(parentController, $element, tagName, superTagNameList) {
  var gTagName = (0, _sdc_utils.tagNameToCamelCase)(tagName);
  if (Global[gTagName]) {
    var controller = Global[gTagName];
    setParentController(parentController, controller);
    controller.$container = $element;
    return controller;
  }
  return controllerFactoryInstance(parentController, $element, tagName, superTagNameList);
}

/**
 * runControllerShow first runs onLoad and fill content for all sub
 * controller. Only if all the sub controller are loaded the willShow
 * control flow function gets called.
 *
 * @param {AbstractSDC} controller - js controller instance
 * @param {jquery} $html - jQuery loaded content
 * @return {Promise<*>} - return of the onLoad function
 */
function runControllerShow(controller, $html) {
  return (0, _sdc_view.runControllerFillContent)(controller, $html).then(function (args) {
    args = args || true;
    if (controller.willShow) {
      var loadPromiseOrContent = controller.willShow();
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
 * runControllerLoad Calls the onLoad function of the controller.
 * This function is called before the HTML is set to the page.
 * The parameter is a list of children of the tag and the registered tag.
 *
 * @param {AbstractSDC} controller - js controller instance
 * @return {Promise<*>} - return of the onLoad function
 */
function runControllerLoad(controller) {
  return (0, _sdc_view.loadFilesFromController)(controller).then(function (html) {
    if (!controller.onLoad || controller._onLoadDone) {
      return html;
    }
    controller._onLoadDone = true;
    var loadPromise = controller.onLoad(html);
    return (loadPromise || (0, _sdc_utils.promiseDummyFactory)()).then(function () {
      return html;
    });
  });
}

/**
 * runControlFlowFunctions runs the control flow functions:
 * 1. onLoad()
 * 2. fill content
 * 3. willShow(dom parameter)
 * 4. refresh()
 *
 * @param controller
 */
function runControlFlowFunctions(controller) {
  var prom_controller = runControllerLoad(controller).then(function ($html) {
    return runControllerShow(controller, $html);
  }).then(function () {
    return controller.refresh && controller.refresh();
  });
  if (controller.load_async) {
    return Promise.resolve();
  }
  return prom_controller;
}