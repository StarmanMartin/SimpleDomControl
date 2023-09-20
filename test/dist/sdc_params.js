"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.getUrlParam = getUrlParam;
exports.runOnInitWithParameter = runOnInitWithParameter;
var _sdc_utils = require("./sdc_utils.js");
var _sdc_view = require("./sdc_view.js");
function getParamList(paramNameList, $element) {
  var returnList;
  if (!paramNameList) {
    paramNameList = [];
  }
  var data = $element.data();
  var restdata = {};
  for (var a in data) {
    if (data.hasOwnProperty(a) && a !== _sdc_view.DATA_CONTROLLER_KEY && !paramNameList.includes(a)) {
      restdata[a] = data[a];
    }
  }
  returnList = [];
  for (var i = 0; i < paramNameList.length; i++) {
    var data_name = paramNameList[i];
    if (data.hasOwnProperty(data_name)) {
      returnList.push(data[data_name]);
    } else {
      returnList.push('undefined');
    }
  }
  returnList.push(restdata);
  return returnList;
}
function parseParamNameList(list) {
  var controller = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
  var values = [];
  for (var i = 0; i < list.length; i++) {
    var tempValue = (0, _sdc_utils.checkIfParamNumberBoolOrString)(list[i], controller);
    values.push(tempValue);
  }
  return values;
}
function getDomTagParamsWithList(paramNameList, $element) {
  var controller = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
  var paramList = getParamList(paramNameList, $element);
  return parseParamNameList(paramList, controller);
}

/**
 *
 * @param {AbstractSDC} controller
 * @param {jquery} $element
 * @param applyController
 * @returns {boolean}
 */
function reg_runOnInitWithParameter(controller, $element, applyController) {
  if (!controller) {
    return false;
  } else if (typeof controller.onInit !== 'function') {
    return false;
  }
  var paramNameList;
  if (typeof controller._on_init_params === 'function') {
    paramNameList = controller._on_init_params();
  } else {
    paramNameList = (0, _sdc_utils.getParamsNameOfFunction)(controller.onInit);
  }
  var initParams = getDomTagParamsWithList(paramNameList, $element, applyController._parentController);
  controller.onInit.apply(applyController, initParams);
  if (applyController === controller) {
    for (var mixinKey in controller._mixins) {
      reg_runOnInitWithParameter(controller._mixins[mixinKey], $element, applyController);
    }
  }
}
function runOnInitWithParameter($element, controller) {
  reg_runOnInitWithParameter(controller, $element, controller);
}
function getUrlParam(controller, $element) {
  return getDomTagParamsWithList(controller._urlParams, $element);
}