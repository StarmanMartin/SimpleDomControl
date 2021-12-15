/**
 * Reference to the HTML body.
 * @type {*|jQuery|HTMLElement}
 * @private
 */
let _$body;
const arg_names_reg = /([^\s,]+)/g;
const commend_reg = /((\/\/.*$)|(\/\*[\s\S]*?\*\/))/mg;

/**
 * getBody returns the $body jQuery object.
 *
 * @returns {*|jQuery|HTMLElement} - body reference.
 */
export function getBody() {
    if (!_$body) {
        _$body = $('body');
    }

    return _$body;
}


/**
 *
 * @param {function} func
 * @returns {RegExpMatchArray|*[]}
 */
export function getParamsNameOfFunction(func) {
    var fnstr = func.toString().replace(commend_reg, '');
    var result = fnstr.slice(fnstr.indexOf('(') + 1, fnstr.indexOf(')')).match(arg_names_reg);
    if (!result) {
        return [];
    }

    return result;
}

/**
 * promiseDummyFactory generates a simple promise which returns instantly.
 * @return {Promise} window.utils
 */
export function promiseDummyFactory() {
    return new Promise(function (resolve) {
        resolve();
    });
}

export function camelCaseToTagName(str) {
    str = str.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
    str = str.replace(/[0-9]+/g, number => `-${number}`);
    return str.replace(/^[-]/g, ``);
}

export function tagNameToCamelCase(str) {
    str = str.replace(/-./g, letter => `${letter[1].toUpperCase()}` );
    return str;
}

const copyProps = (targetClass, sourceClass) => {
    let source = sourceClass;
    let propNamesTarget =  Object.getOwnPropertyNames(targetClass.prototype).concat(Object.getOwnPropertySymbols(targetClass.prototype))
    while (source.name !== '') {
        Object.getOwnPropertyNames(source.prototype)
            .concat(Object.getOwnPropertySymbols(source.prototype))
            .forEach((prop) => {
                if (prop.match(/^(?:constructor|prototype|arguments|caller|name|bind|call|apply|toString|length)$/)) {
                    return;
                }

                if(!propNamesTarget.includes(prop)) {
                    propNamesTarget.push(prop);
                    Object.defineProperty(targetClass.prototype, prop, Object.getOwnPropertyDescriptor(source.prototype, prop));
                }
            });
        source = Object.getPrototypeOf(source);
    }
}

/**
 *
 * @param {AbstractSDC} baseClass
 * @param {AbstractSDC} mixins
 * @returns {AbstractSDC}
 */
export function agileAggregation (baseClass, ...mixins) {

    let base = class _Combined {
        constructor(...args) {
            let _mixins = {};
            mixins.forEach((mixin) => {
                let newMixin;
                Object.assign(this, (newMixin = new mixin()));
                _mixins[mixin.name] = newMixin;
            });

            Object.assign(this, new baseClass());
            this._mixins = _mixins;
        }

        get mixins() {
            return this._mixins;
        }
    };

    copyProps(base, baseClass);

    mixins.forEach((mixin) => {
        copyProps(base, mixin);
    });

    return base;

}

export function uploadFileFormData(formData, url, method) {
    return $.ajax({
        url: url,  //Server script to process data
        type: method || 'POST',
        xhr: function () {  // Custom XMLHttpRequest
            var myXhr = $.ajaxSettings.xhr();
            if (myXhr.upload) { // Check if upload property exists
                myXhr.upload.addEventListener('progress', progressHandlingFunction, false); // For handling the progress of the upload
            }
            return myXhr;
        },
        //Form data
        data: formData,
        //Options to tell jQuery not to process data or worry about content-type.
        cache: false,
        contentType: false,
        processData: false
    });
}

function progressHandlingFunction(e) {
    if (e.lengthComputable) {
        var percentVal = Math.round((e.loaded / e.total) * 100);
        var $progressContainer = $('.progress-container');
        if(percentVal === 100) {
            $progressContainer.hide();
        } else {
            $progressContainer.show();
        }

        percentVal += '%';

        $progressContainer.find('.progress-bar').css({'width': percentVal}).text(percentVal);
    }
}


export function checkIfParamNumberBoolOrString(paramElement) {
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

export function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}