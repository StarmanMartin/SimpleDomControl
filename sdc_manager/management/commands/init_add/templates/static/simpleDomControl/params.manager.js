(function (app) {
    /**
     * The public parameter manager objects
     * @type {{}}
     */
    var pm = app.paramManager = {};

    var innerReplaceToken = "#_TOKEN_#_REPLACE_#_INNER_#";
    var innerReplaceTokenReg = new RegExp(innerReplaceToken, 'g');

    pm.runOnInitWithParameter = function (controller, $element) {
        reg_runOnInitWithParameter(controller, $element, controller);
    };

    pm.getUrlParam = function (controller, $element) {
        return getDomTagParamsWithList(controller, $element, controller._urlParams);
    };

    function reg_runOnInitWithParameter(controller, $element, applyController) {
        if (!controller) {
            return false
        } else if (typeof controller.onInit !== 'function') {
            return reg_runOnInitWithParameter(controller.super, $element, applyController);
        }

        let paramNameList = window.utils.getParamsNameOfFunction(controller.onInit);
        let initParams = getDomTagParamsWithList(controller, $element, paramNameList);
        controller.onInit.apply(applyController, initParams);
        reg_runOnInitWithParameter(controller.super, $element, applyController);
    }

    function getDomTagParamsWithList(controller, $element, paramNameList) {
        let paramList = pm.getParamList(paramNameList, $element);
        return pm.parse(controller.parentController, paramList);
    }

    pm.getParamList = function (paramNameList, $element) {
        var returnList, paramListAsString = '';

        if (!paramNameList) {
            paramNameList = [];
        }
        returnList = [];
        for (var i = 0; i < paramNameList.length; i++) {
            let data_name = app.domRouter.makeTag(paramNameList[i]);
            if ($element.attr('data-' + data_name)) {
                returnList.push($element.data(data_name));
            } else {
                returnList.push('undefined');
            }
        }

        paramListAsString = returnList.join(' ');

        if (!paramListAsString) {
            return [];
        }

        return pm.splitParamList(paramListAsString);
    };

    pm.parse = function (parentController, paramList) {
        if(!paramList) {
            return [];
        }

        if (!parentController){
            parentController = {};
        }

        return parseParamNameList(parentController, paramList);
    };

    pm.splitParamList = function(paramListAsString){
        paramListAsString = '' + paramListAsString;
        return splitParamList(paramListAsString.replace(/(\[[^\]]*\])/g, function (match, val) {
            return '.' + val.replace(/\./g, innerReplaceToken);
        }));
    };

    function splitParamList(list) {
        var currentElement = '';
        var elementList = [];
        var isString = false;
        for (var letter = 0; letter < list.length; letter++) {
            if (list[letter] === ' ' && !isString) {
                elementList.push(currentElement);
                currentElement = '';
            } else if (currentElement === "" && list[letter] === "'") {
                isString = true;
                currentElement += list[letter];
            } else if (list[letter] === "'" && isString) {
                isString = false;
                currentElement += list[letter];
            } else {
                currentElement += list[letter];
            }
        }

        elementList.push(currentElement);

        return elementList;
    }

    function parseParamNameList(controller, list) {

        var values = [];

        for (var i = 0; i < list.length; i++) {
            var checkResult = checkIfParamNumberBoolOrString(list[i]);
            var tempValue;
            if (checkResult.isSimpleValue) {
                tempValue = checkResult.value;
            } else {
                tempValue = getParamValue(controller, list[i]);
            }

            values.push(tempValue);
        }

        return values;
    }

    function getParamValue(controller, key) {
        var keyList = key.split('.');
        var valueByValueReg = /^\[([^\]]*)\]$/;

        function getParamValueFromObject(startObject) {
            for (var l = 0; l < keyList.length; l++) {
                var nextKey = keyList[l];
                var result = valueByValueReg.exec(nextKey);
                if (result) {

                    nextKey = getParamValue(controller, result[1].replace(innerReplaceTokenReg(), '.'));
                    if (!nextKey) {
                        return undefined;
                    }
                }

                startObject = startObject[nextKey];
                if (typeof startObject === 'undefined') {
                    return startObject;
                }
            }

            return startObject;
        }

        while (controller) {
            var value = getParamValueFromObject(controller);
            if (typeof value !== 'undefined') {
                return value;
            }

            controller = controller.parentController;
        }

        console.error("Constructor variable not found", key);
    }

    function checkIfParamNumberBoolOrString(paramElement) {
        var isStringReg = /^(['][^']*['])|(["][^"]*["])$/;
        var isFloatReg = /^\d+\.?\d+$/;
        var isIntReg = /^\d+$/;
        var isBoolReg = /^(true|false)$/;

        var returnObject = {};

        if (paramElement.match(isBoolReg)) {
            returnObject.isSimpleValue = true;
            returnObject.value = paramElement === 'true';
        } else if (paramElement === 'undefined') {
            returnObject.isSimpleValue = true;
            returnObject.value = undefined;
        } else if (paramElement.match(isStringReg)) {
            returnObject.isSimpleValue = true;
            returnObject.value = paramElement.substr(1, paramElement.length - 2);
        } else if (paramElement.match(isIntReg)) {
            returnObject.isSimpleValue = true;
            returnObject.value = parseInt(paramElement);
        } else if (paramElement.match(isFloatReg)) {
            returnObject.isSimpleValue = true;
            returnObject.value = parseFloat(paramElement);
        }

        return returnObject;
    }


})(window.app || (window.app = {}));


