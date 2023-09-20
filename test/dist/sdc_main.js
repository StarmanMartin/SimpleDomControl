"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.app = void 0;
var _sdc_utils = require("./sdc_utils.js");
var _sdc_view = require("./sdc_view.js");
var _AbstractSDC = require("./AbstractSDC.js");
var _sdc_controller = require("./sdc_controller.js");
var _sdc_dom_events = require("./sdc_dom_events.js");
var _sdc_events = require("./sdc_events.js");
var _sdc_socket = require("./sdc_socket.js");
var app = {
  CSRF_TOKEN: window.CSRF_TOKEN || '',
  LANGUAGE_CODE: window.LANGUAGE_CODE || 'en',
  DEBUG: window.DEBUG || false,
  VERSION: window.VERSION || '0.0',
  tagNames: [],
  Global: _sdc_controller.Global,
  rootController: null,
  init_sdc: function init_sdc() {
    var old_trigger = $.fn.trigger;
    $.fn.trigger = function (event) {
      var ev_type = {}.hasOwnProperty.call(event, "type") ? event.type : event;
      if (!_sdc_dom_events.STD_EVENT_LIST.includes(ev_type)) {
        _sdc_dom_events.STD_EVENT_LIST.push(ev_type);
        $(window).on(ev_type, _sdc_dom_events.windowEventHandler);
      }
      return old_trigger.call(this, event);
    };
    $.fn.safeReplace = function ($elem) {
      return app.safeReplace($(this), $elem);
    };
    $.fn.safeEmpty = function () {
      return app.safeEmpty($(this));
    };
    $.fn.safeRemove = function () {
      return app.safeRemove($(this));
    };
    (0, _sdc_socket.isConnected)();
    (0, _sdc_dom_events.initEvents)();
    app.rootController = app.rootController || new _AbstractSDC.AbstractSDC();
    app.tagNames = Object.keys(_sdc_controller.controllerList);
    return (0, _sdc_view.replaceTagElementsInContainer)(app.tagNames, (0, _sdc_utils.getBody)(), app.rootController);
  },
  controllerToTag: function controllerToTag(Controller) {
    var tagName = (0, _sdc_utils.camelCaseToTagName)(Controller.name);
    return tagName.replace(/-controller$/, '');
  },
  /**
   *
   * @param {AbstractSDC} Controller
   */
  registerGlobal: function registerGlobal(Controller) {
    var tagName = app.controllerToTag(Controller);
    var globalController = new Controller();
    _sdc_controller.controllerList[tagName] = [globalController, []];
    globalController._tagName = tagName;
    _sdc_controller.Global[(0, _sdc_utils.tagNameToCamelCase)(tagName)] = globalController;
  },
  cleanCache: function cleanCache() {
    (0, _sdc_view.cleanCache)();
  },
  /**
   *
   * @param {AbstractSDC} Controller
   */
  register: function register(Controller) {
    var tagName = app.controllerToTag(Controller);
    _sdc_controller.controllerList[tagName] = [Controller, []];
    Controller.prototype._tagName = tagName;
    return {
      /**
       *
       * @param {Array<string>} mixins Controller tag names
       */
      addMixin: function addMixin() {
        for (var _len = arguments.length, mixins = new Array(_len), _key = 0; _key < _len; _key++) {
          mixins[_key] = arguments[_key];
        }
        for (var _i = 0, _mixins = mixins; _i < _mixins.length; _i++) {
          var mixin = _mixins[_i];
          var mixinName = void 0;
          if (typeof mixin === "string") {
            mixinName = (0, _sdc_utils.camelCaseToTagName)(mixin);
          } else if (mixin) {
            mixinName = app.controllerToTag(mixin);
          }
          _sdc_controller.controllerList[tagName][1].push(mixinName);
        }
      }
    };
  },
  /**
   *
   * @param {AbstractSDC} controller
   * @param {string} url
   * @param {object} args
   * @return {Promise}
   */
  post: function post(controller, url, args) {
    if (!args) {
      args = {};
    }
    args.CSRF_TOKEN = app.CSRF_TOKEN;
    return app.ajax(controller, url, params, $.post);
  },
  /**
   *
   * @param {AbstractSDC} controller
   * @param {string} url
   * @param {object} args
   * @return {Promise}
   */
  get: function get(controller, url, args) {
    return app.ajax(controller, url, args, $.get);
  },
  /**
   *
   * @param {AbstractSDC} controller
   * @param {string} url
   * @param {object} args
   * @param {function} method $.get or $.post
   * @return {Promise}
   */
  ajax: function ajax(controller, url, args, method) {
    if (!args) {
      args = {};
    }
    args.VERSION = app.VERSION;
    args._method = args._method || 'api';
    var p = new Promise(function (resolve, reject) {
      return method(url, args).then(function (a, b, c) {
        resolve(a, b, c);
        if (a.status === 'redirect') {
          (0, _sdc_events.trigger)('onNavLink', a['url-link']);
        } else {
          p.then(function () {
            app.refresh(controller.$container);
          });
        }
      })["catch"](reject);
    });
    return p;
  },
  submitFormAndUpdateView: function submitFormAndUpdateView(controller, form, url, method) {
    var formData = new FormData(form);
    var p = new Promise(function (resolve, reject) {
      (0, _sdc_utils.uploadFileFormData)(formData, url || form.action, method || form.method).then(function (a, b, c) {
        resolve(a, b, c);
        if (a.status === 'redirect') {
          if (a['url-link']) {
            (0, _sdc_events.trigger)('onNavLink', a['url-link']);
          } else {
            window.location.href = a['url'];
          }
        } else {
          p.then(function () {
            app.refresh(controller.$container);
          });
        }
      })["catch"](reject);
    });
    return p;
  },
  submitForm: function submitForm(form, url, method) {
    var formData = new FormData(form);
    return new Promise(function (resolve, reject) {
      (0, _sdc_utils.uploadFileFormData)(formData, url || form.action, method || form.method).then(resolve)["catch"](reject);
    });
  },
  /**
   *
   * @param {jquery} $elem
   * @return {AbstractSDC}
   */
  getController: function getController($elem) {
    return (0, _sdc_view.getController)($elem);
  },
  /**
   * safeEmpty removes all content of a dom
   * and deletes all child controller safely.
   *
   * @param $elem - jQuery DOM container to be emptyed
   */
  safeEmpty: function safeEmpty($elem) {
    var $children = $elem.children();
    $children.each(function (_, element) {
      var $element = $(element);
      app.safeRemove($element);
    });
    return $elem;
  },
  /**
   * safeReplace removes all content of a dom
   * and deletes all child controller safely.
   *
   * @param $elem - jQuery DOM to be repleaced
   * @param $new - jQuery new DOM container
   */
  safeReplace: function safeReplace($elem, $new) {
    $new.insertBefore($elem);
    return app.safeRemove($elem);
  },
  /**
   * safeRemove removes a dom and deletes all child controller safely.
   *
   * @param $elem - jQuery Dom
   */
  safeRemove: function safeRemove($elem) {
    $elem.each(function () {
      var $this = $(this);
      if ($this.data("".concat(_sdc_view.DATA_CONTROLLER_KEY))) {
        $this.data("".concat(_sdc_view.DATA_CONTROLLER_KEY)).remove();
      }
    });
    $elem.find(".".concat(_sdc_view.CONTROLLER_CLASS)).each(function () {
      var controller = $(this).data("".concat(_sdc_view.DATA_CONTROLLER_KEY));
      controller && controller.remove();
    });
    return $elem.remove();
  },
  /**
   *
   * @param {AbstractSDC} controller
   * @return {Promise<jQuery>}
   */
  reloadController: function reloadController(controller) {
    return (0, _sdc_view.reloadHTMLController)(controller).then(function (html) {
      var $html = $(html);
      controller._childController = {};
      (0, _sdc_view.replaceTagElementsInContainer)(app.tagNames, $html, controller).then(function () {
        app.safeEmpty(controller.$container);
        controller.$container.append($html);
        app.refresh(controller.$container, controller);
      });
    });
  },
  /**
   *
   * @param {jquery} $container
   * @param {AbstractSDC} leafController
   * @return {Promise<jQuery>}
   */
  refresh: function refresh($container, leafController) {
    if (!leafController) {
      leafController = app.getController($container);
    }
    if (!leafController) {
      return (0, _sdc_utils.promiseDummyFactory)();
    }
    var controller = leafController;
    var controllerList = [];
    while (controller) {
      controller.isEventsSet = false;
      controllerList.unshift(controller);
      controller = controller._parentController;
    }
    return (0, _sdc_view.replaceTagElementsInContainer)(app.tagNames, leafController.$container, leafController).then(function () {
      for (var _i2 = 0, _controllerList = controllerList; _i2 < _controllerList.length; _i2++) {
        var con = _controllerList[_i2];
        (0, _sdc_dom_events.setControllerEvents)(con);
        con.onRefresh($container);
      }
    });
  }
};
exports.app = app;