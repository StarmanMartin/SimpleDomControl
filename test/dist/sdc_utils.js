"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.agileAggregation = agileAggregation;
exports.camelCaseToTagName = camelCaseToTagName;
exports.checkIfParamNumberBoolOrString = checkIfParamNumberBoolOrString;
exports.clearErrorsInForm = clearErrorsInForm;
exports.getBody = getBody;
exports.getParamsNameOfFunction = getParamsNameOfFunction;
exports.promiseDummyFactory = promiseDummyFactory;
exports.setErrorsInForm = setErrorsInForm;
exports.tagNameToCamelCase = tagNameToCamelCase;
exports.tagNameToReadableName = tagNameToReadableName;
exports.uploadFileFormData = uploadFileFormData;
exports.uuidv4 = uuidv4;
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }
function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, _toPropertyKey(descriptor.key), descriptor); } }
function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); Object.defineProperty(Constructor, "prototype", { writable: false }); return Constructor; }
function _toPropertyKey(arg) { var key = _toPrimitive(arg, "string"); return _typeof(key) === "symbol" ? key : String(key); }
function _toPrimitive(input, hint) { if (_typeof(input) !== "object" || input === null) return input; var prim = input[Symbol.toPrimitive]; if (prim !== undefined) { var res = prim.call(input, hint || "default"); if (_typeof(res) !== "object") return res; throw new TypeError("@@toPrimitive must return a primitive value."); } return (hint === "string" ? String : Number)(input); }
/**
 * Reference to the HTML body.
 * @type {*|jQuery|HTMLElement}
 * @private
 */
var _$body;
var arg_names_reg = /([^\s,]+)/g;
var commend_reg = /((\/\/.*$)|(\/\*[\s\S]*?\*\/))/mg;

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
 *
 * @param {function} func
 * @returns {RegExpMatchArray|*[]}
 */
function getParamsNameOfFunction(func) {
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
function promiseDummyFactory() {
  return new Promise(function (resolve) {
    resolve();
  });
}
function camelCaseToTagName(str) {
  str = str.replace(/[A-Z]/g, function (letter) {
    return "-".concat(letter.toLowerCase());
  });
  str = str.replace(/[0-9]+/g, function (number) {
    return "-".concat(number);
  });
  return str.replace(/^[-]/g, "");
}
function tagNameToCamelCase(str) {
  str = str.replace(/-./g, function (letter) {
    return "".concat(letter[1].toUpperCase());
  });
  return str;
}
function tagNameToReadableName(str) {
  str = str.replace(/-./g, function (letter) {
    return " ".concat(letter[1].toUpperCase());
  }).replace(/^./g, function (letter) {
    return "".concat(letter.toUpperCase());
  });
  return str;
}
var copyProps = function copyProps(targetClass, sourceClass) {
  var source = sourceClass;
  var propNamesTarget = Object.getOwnPropertyNames(targetClass.prototype).concat(Object.getOwnPropertySymbols(targetClass.prototype));
  while (source.name !== '') {
    Object.getOwnPropertyNames(source.prototype).concat(Object.getOwnPropertySymbols(source.prototype)).forEach(function (prop) {
      if (prop.match(/^(?:constructor|prototype|arguments|caller|name|bind|call|apply|toString|length)$/)) {
        return;
      }
      if (!propNamesTarget.includes(prop)) {
        propNamesTarget.push(prop);
        Object.defineProperty(targetClass.prototype, prop, Object.getOwnPropertyDescriptor(source.prototype, prop));
      }
    });
    source = Object.getPrototypeOf(source);
  }
};

/**
 *
 * @param {AbstractSDC} baseClass
 * @param {AbstractSDC} mixins
 * @returns {AbstractSDC}
 */
function agileAggregation(baseClass) {
  for (var _len = arguments.length, mixins = new Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
    mixins[_key - 1] = arguments[_key];
  }
  var base = /*#__PURE__*/function () {
    function _Combined() {
      var _this = this;
      _classCallCheck(this, _Combined);
      var _mixins = {};
      mixins.forEach(function (mixin) {
        var newMixin;
        Object.assign(_this, newMixin = new mixin());
        newMixin._tagName = mixin.prototype._tagName;
        newMixin._isMixin = true;
        _mixins[mixin.name] = newMixin;
      });
      Object.assign(this, new baseClass());
      this._mixins = _mixins;
    }
    _createClass(_Combined, [{
      key: "mixins",
      get: function get() {
        return this._mixins;
      }
    }]);
    return _Combined;
  }();
  copyProps(base, baseClass);
  mixins.forEach(function (mixin) {
    copyProps(base, mixin);
  });
  return base;
}
function csrfSafeMethod(method) {
  // these HTTP methods do not require CSRF protection
  return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}
function uploadFileFormData(formData, url, method) {
  return $.ajax({
    url: url,
    //Server script to process data
    type: method || 'POST',
    xhr: function xhr() {
      // Custom XMLHttpRequest
      var myXhr = $.ajaxSettings.xhr();
      if (myXhr.upload) {
        // Check if upload property exists
        myXhr.upload.addEventListener('progress', progressHandlingFunction, false); // For handling the progress of the upload
      }

      return myXhr;
    },
    //Form data
    data: formData,
    //Options to tell jQuery not to process data or worry about content-type.
    cache: false,
    contentType: false,
    processData: false,
    beforeSend: function beforeSend(xhr, settings) {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", window.CSRF_TOKEN);
      }
    }
  });
}
function progressHandlingFunction(e) {
  if (e.lengthComputable) {
    var percentVal = Math.round(e.loaded / e.total * 100);
    var $progressContainer = $('.progress-container');
    if (percentVal === 100) {
      $progressContainer.hide();
    } else {
      $progressContainer.show();
    }
    percentVal += '%';
    $progressContainer.find('.progress-bar').css({
      'width': percentVal
    }).text(percentVal);
  }
}
function checkIfParamNumberBoolOrString(paramElement) {
  var controller = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
  if (typeof paramElement !== 'string') {
    return paramElement;
  }
  if (controller && typeof controller[paramElement] !== 'undefined') {
    if (typeof controller[paramElement] === 'function') {
      return controller[paramElement].bind(controller);
    }
    return controller[paramElement];
  }
  var isFloatReg = /^-?\d+\.?\d+$/;
  var isIntReg = /^-?\d+$/;
  var isBoolReg = /^(true|false)$/;
  var isStringReg = /^(['][^']*['])|(["][^"]*["])$/;
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
function uuidv4() {
  return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, function (c) {
    return (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16);
  });
}
function clearErrorsInForm($form) {
  $form.find('.has-error').removeClass('has-error').find('.alert-danger').remove();
  $form.find('.non-field-errors').remove();
}
function setErrorsInForm($form, $resForm) {
  $resForm = $('<div>').append($resForm);
  $form.find('.has-error').removeClass('has-error').find('.alert-danger').safeRemove();
  $form.find('.non-field-errors').safeRemove();
  var $file_container = $resForm.find('input[type=file]').parent();
  $form.find('input[type=file]').parent().each(function (index) {
    $(this).replaceWith($file_container[index]);
  });
  var hasNoError = $resForm.find('.non-field-errors').insertAfter($form.find('.hidden-form-fields')).length === 0;
  $resForm.find('.has-error').each(function () {
    hasNoError = false;
    var $resErrorField = $(this);
    var className = $resErrorField.data('auto-id');
    var $errorField = $form.find('.form-group.' + className);
    $errorField.addClass('has-error');
    $errorField.find('.form-input-container').append($resErrorField.find('.alert-danger'));
  });
  return hasNoError;
}