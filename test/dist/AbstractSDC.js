"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.AbstractSDC = void 0;
var _sdc_events = require("./sdc_events.js");
var _sdc_main = require("./sdc_main.js");
var _sdc_socket = require("./sdc_socket.js");
var _sdc_utils = require("./sdc_utils.js");
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _toConsumableArray(arr) { return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _unsupportedIterableToArray(arr) || _nonIterableSpread(); }
function _nonIterableSpread() { throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _iterableToArray(iter) { if (typeof Symbol !== "undefined" && iter[Symbol.iterator] != null || iter["@@iterator"] != null) return Array.from(iter); }
function _arrayWithoutHoles(arr) { if (Array.isArray(arr)) return _arrayLikeToArray(arr); }
function _createForOfIteratorHelper(o, allowArrayLike) { var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"]; if (!it) { if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") { if (it) o = it; var i = 0; var F = function F() {}; return { s: F, n: function n() { if (i >= o.length) return { done: true }; return { done: false, value: o[i++] }; }, e: function e(_e) { throw _e; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var normalCompletion = true, didErr = false, err; return { s: function s() { it = it.call(o); }, n: function n() { var step = it.next(); normalCompletion = step.done; return step; }, e: function e(_e2) { didErr = true; err = _e2; }, f: function f() { try { if (!normalCompletion && it["return"] != null) it["return"](); } finally { if (didErr) throw err; } } }; }
function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }
function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i]; return arr2; }
function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }
function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, _toPropertyKey(descriptor.key), descriptor); } }
function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); Object.defineProperty(Constructor, "prototype", { writable: false }); return Constructor; }
function _toPropertyKey(arg) { var key = _toPrimitive(arg, "string"); return _typeof(key) === "symbol" ? key : String(key); }
function _toPrimitive(input, hint) { if (_typeof(input) !== "object" || input === null) return input; var prim = input[Symbol.toPrimitive]; if (prim !== undefined) { var res = prim.call(input, hint || "default"); if (_typeof(res) !== "object") return res; throw new TypeError("@@toPrimitive must return a primitive value."); } return (hint === "string" ? String : Number)(input); }
var AbstractSDC = /*#__PURE__*/function () {
  function AbstractSDC() {
    _classCallCheck(this, AbstractSDC);
    this._uuid = (0, _sdc_utils.uuidv4)();
    this.contentUrl = '';
    this.contentReload = false;
    this.hasSubnavView = false;
    this.events = [];
    this.load_async = false;
    this.isEventsSet = false;
    this._allEvents = null;
    this._urlParams = [];
    this._models = [];

    // ------------------ Old deprecated properties ----------------------
    this._cssUrls = [];
    this.afterShow = function () {
      console.warn('afterShow is deprecated!!');
    };
    // -------------- End old deprecated properties ----------------------

    /**
     *
     * @type {{string: AbstractSDC}}
     */
    this._mixins = {};

    /**
     * @type {string}
     */
    this._tagName = '';

    /**
     * @type {{string:AbstractSDC}}
     */
    this._childController = {};

    /**
     * @type {AbstractSDC}
     */
    this._parentController = null;

    /**
     * @type {boolean}
     */
    this._onLoadDone = false;

    /**
     * @type {jquery}
     */
    this.$container = null;

    /**
     *
     * @type {boolean}
     */
    this._isMixin = false;
  }

  /**
   *
   * @param {string} method must be in {}
   * @param {Array} args in arguments of
   *
   */
  _createClass(AbstractSDC, [{
    key: "_runLifecycle",
    value: function _runLifecycle(method, args) {
      var _this = this;
      if (_sdc_main.app.DEBUG) {
        console.debug(method, this._tagName);
      }
      var returnPromisses = [];
      if (this._isMixin) {
        return;
      }
      this._isMixin = true;
      for (var mixinKey in this._mixins) {
        var mixin = this._mixins[mixinKey];
        if (typeof mixin[method] === 'function') {
          returnPromisses.push(mixin[method].apply(this, args));
        }
      }
      return Promise.all(returnPromisses).then(function () {
        _this._isMixin = false;
      });
    }
  }, {
    key: "onInit",
    value: function onInit() {
      if (_sdc_main.app.DEBUG) {
        console.DEBUG(Array.apply(null, arguments), this._tagName);
      }
    }
  }, {
    key: "onLoad",
    value: function onLoad() {
      return this._runLifecycle('onLoad', arguments);
    }
  }, {
    key: "willShow",
    value: function willShow() {
      return this._runLifecycle('willShow', arguments);
    }
  }, {
    key: "onRefresh",
    value: function onRefresh() {
      return this._runLifecycle('onRefresh', arguments);
    }
  }, {
    key: "onRemove",
    value: function onRemove() {
      this._runLifecycle('onRemove', arguments);
      return true;
    }
  }, {
    key: "remove",
    value: function remove() {
      var _iterator = _createForOfIteratorHelper(this._models),
        _step;
      try {
        for (_iterator.s(); !(_step = _iterator.n()).done;) {
          var model = _step.value;
          model.close();
        }
      } catch (err) {
        _iterator.e(err);
      } finally {
        _iterator.f();
      }
      var _childController = this._childController;
      for (var i in _childController) {
        if (_childController.hasOwnProperty(i)) {
          var _iterator2 = _createForOfIteratorHelper(_childController[i]),
            _step2;
          try {
            for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
              var cc = _step2.value;
              if (!cc.remove()) {
                return false;
              }
            }
          } catch (err) {
            _iterator2.e(err);
          } finally {
            _iterator2.f();
          }
        }
      }
      if (!this.onRemove || this.onRemove()) {
        (0, _sdc_events.allOff)(this);
        var c_name = (0, _sdc_utils.tagNameToCamelCase)(this._tagName);
        if (this._parentController._childController[c_name]) {
          var arr = this._parentController._childController[c_name];
          for (var _i = 0; _i < arr.length; _i++) {
            if (arr[_i] === this) {
              arr.splice(_i, 1);
            }
          }
        }
        this.$container.remove();
        delete this;
        return true;
      }
      return false;
    }
  }, {
    key: "controller_name",
    value: function controller_name() {
      return (0, _sdc_utils.tagNameToReadableName)(this._tagName);
    }
  }, {
    key: "addEvent",
    value: function addEvent(event, selector, handler) {
      this.getEvents();
      this._allEvents[event] = this._allEvents[event] || {};
      this._allEvents[event][selector] = handler;
    }
  }, {
    key: "getEvents",
    value: function getEvents() {
      if (this._allEvents) return this._allEvents;
      var allEvents = [];
      allEvents = allEvents.concat(this.events);
      for (var mixinKey in this._mixins) {
        var mixin = this._mixins[mixinKey];
        if (Array.isArray(mixin.events)) {
          allEvents = allEvents.concat(mixin.events);
        }
      }
      return this._allEvents = Object.assign.apply(Object, [{}].concat(_toConsumableArray(allEvents)));
    }
  }, {
    key: "post",
    value: function post(url, args) {
      return _sdc_main.app.post(this, url, args);
    }
  }, {
    key: "get",
    value: function get(url, args) {
      return _sdc_main.app.get(this, url, args);
    }
  }, {
    key: "submitForm",
    value: function submitForm(form, url, method) {
      return _sdc_main.app.submitFormAndUpdateView(this, form, url, method);
    }
  }, {
    key: "serverCall",
    value: function serverCall(methode, args) {
      var re = /sdc_view\/([^/]+)/i;
      var app = this.contentUrl.match(re);
      if (!app || app.length < 2) {
        console.error('To use the serverCall function the contentUrl must be set: ' + this.name);
        return;
      }
      return (0, _sdc_socket.callServer)(app[1], this._tagName, methode, args);
    }

    /**
     *
     * @param model_name {string}
     * @param model_query {Object}
     * @constructor
     */
  }, {
    key: "newModel",
    value: function newModel(model_name) {
      var model_query = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
      var model = new _sdc_socket.Model(model_name, model_query);
      this._models.push(model);
      return model;
    }

    /**
     * Adapter to this.$container.find
     * @param {string} domSelector
     */
  }, {
    key: "find",
    value: function find(domSelector) {
      return this.$container.find(domSelector);
    }
  }, {
    key: "refresh",
    value: function refresh() {
      return _sdc_main.app.refresh(this.$container, this);
    }
  }, {
    key: "reload",
    value: function reload() {
      return _sdc_main.app.reloadController(this);
    }

    /**
     * Model Form Events
     */
  }, {
    key: "_submitModelForm",
    value: function _submitModelForm($form, e) {
      var p_list = [];
      if (!this._isMixin) {
        e.stopPropagation();
        e.preventDefault();
        var model = $form.data('model');
        var values = model.syncForm($form);
        var _iterator3 = _createForOfIteratorHelper(values),
          _step3;
        try {
          var _loop = function _loop() {
            var instance_value = _step3.value;
            p_list.push(new Promise(function (resolve, reject) {
              var prom;
              if (instance_value.pk !== null) {
                prom = model.save(instance_value.pk);
              } else {
                prom = model.create(instance_value);
              }
              prom.then(function (res) {
                (0, _sdc_utils.clearErrorsInForm)($form);
                resolve(res);
              })["catch"](function (data) {
                (0, _sdc_utils.setErrorsInForm)($form, $(data.html));
                reject(data);
              });
            }));
          };
          for (_iterator3.s(); !(_step3 = _iterator3.n()).done;) {
            _loop();
          }
        } catch (err) {
          _iterator3.e(err);
        } finally {
          _iterator3.f();
        }
      }
      return Promise.all(p_list).then(function (res) {
        return Object.assign.apply(Object, [{}].concat(_toConsumableArray(res.flat())));
      });
    }
  }]);
  return AbstractSDC;
}();
exports.AbstractSDC = AbstractSDC;