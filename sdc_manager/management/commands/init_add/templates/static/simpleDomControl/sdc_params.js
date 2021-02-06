import {getParamsNameOfFunction,camelCaseToTagName} from "./sdc_utils.js";

/**
 *
 * @param {AbstractSDC} controller
 * @param {jquery} $element
 * @param applyController
 * @returns {boolean}
 */
function reg_runOnInitWithParameter(controller, $element, applyController) {
    if (!controller) {
        return false
    } else if (typeof controller.onInit !== 'function') {
        return false
    }

    let paramNameList = getParamsNameOfFunction(controller.onInit);
    let initParams = getDomTagParamsWithList(paramNameList, $element);
    controller.onInit.apply(applyController, initParams);
    if(applyController === controller) {
        for (let mixinKey in controller._mixins) {
            reg_runOnInitWithParameter(controller._mixins[mixinKey], $element, applyController);
        }
    }
}

function getDomTagParamsWithList(paramNameList, $element) {
    let paramList = getParamList(paramNameList, $element);
    return parseParamNameList(paramList);
}

export function runOnInitWithParameter($element, controller) {
    reg_runOnInitWithParameter(controller, $element, controller);
}

export function getUrlParam($element) {
    return getDomTagParamsWithList(controller._urlParams, $element);
}

function getParamList(paramNameList, $element) {
    var returnList, paramListAsString = '';

    if (!paramNameList) {
        paramNameList = [];
    }
    returnList = [];
    for (let i = 0; i < paramNameList.length; i++) {
        let data_name = camelCaseToTagName(paramNameList[i]);
        if ($element.attr('data-' + data_name)) {
            returnList.push($element.data(data_name));
        } else {
            returnList.push('undefined');
        }
    }

    return returnList;
}

function parseParamNameList(list) {
    let values = [];

    for (let i = 0; i < list.length; i++) {
        let tempValue = checkIfParamNumberBoolOrString(list[i]);
        values.push(tempValue);
    }

    return values;
}

function checkIfParamNumberBoolOrString(paramElement) {
    if(typeof paramElement !== 'string') {
        return paramElement;
    }

    let isFloatReg = /^-?\d+\.?\d+$/;
    let isIntReg = /^-?\d+$/;
    let isBoolReg = /^(true|false)$/;
    let isStringReg = /^(['][^']*['])|(["][^"]*["])$/;

    if (paramElement.match(isBoolReg)) {
        return paramElement === 'true';
    } else if (paramElement === 'undefined') {
        return undefined;
    } else if (paramElement.toLowerCase() === 'none') {
        return null;
    } else if (paramElement.match(isIntReg)) {
        return parseInt(paramElement);
    } else if (paramElement.match(isFloatReg)) {
        return parseFloat(paramElement);
    } else if (paramElement.match(isStringReg)) {
        return paramElement.substr(1, paramElement.length - 2);
    }

    return paramElement;
}



