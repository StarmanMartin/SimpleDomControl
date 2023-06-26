import {getParamsNameOfFunction, checkIfParamNumberBoolOrString} from "./sdc_utils.js";
import {DATA_CONTROLLER_KEY} from "./sdc_view.js";




function getParamList(paramNameList, $element) {
    let returnList;
    if (!paramNameList) {
        paramNameList = [];
    }

    let data = $element.data();
    let restdata = {};
    for(let a in data) {
        if(data.hasOwnProperty(a) && a !== DATA_CONTROLLER_KEY && !paramNameList.includes(a)) {
            restdata[a] = data[a];
        }
    }

    returnList = [];
    for (let i = 0; i < paramNameList.length; i++) {
        let data_name = paramNameList[i];

        if (data.hasOwnProperty(data_name)) {
            returnList.push(data[data_name]);
        } else {
            returnList.push('undefined');
        }
    }

    returnList.push(restdata)
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

function getDomTagParamsWithList(paramNameList, $element) {
    let paramList = getParamList(paramNameList, $element);
    return parseParamNameList(paramList);
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

export function runOnInitWithParameter($element, controller) {
    reg_runOnInitWithParameter(controller, $element, controller);
}

export function getUrlParam(controller, $element) {
    return getDomTagParamsWithList(controller._urlParams, $element);
}