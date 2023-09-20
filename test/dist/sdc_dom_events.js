"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.STD_EVENT_LIST = void 0;
exports.initEvents = initEvents;
exports.setControllerEvents = setControllerEvents;
exports.windowEventHandler = windowEventHandler;
var _sdc_view = require("./sdc_view.js");
var STD_EVENT_LIST = Object.keys(window).filter(function (key) {
  return /^on/.test(key);
}).map(function (x) {
  return x.slice(2);
});
exports.STD_EVENT_LIST = STD_EVENT_LIST;
function windowEventHandler(event) {
  var ev_type = event.type;
  if (event.hasOwnProperty('namespace') && event.namespace && event.namespace.length) ev_type += ".".concat(event.namespace);
  var $elm = $(event.target);
  var controller = null;
  var is_done = false;
  var is_last_elem = false;
  event.stopImmediatePropagation = function () {
    return is_last_elem = true;
  };
  event.stopPropagation = function () {
    return is_last_elem = is_done = true;
  };
  while ($elm.length) {
    var attrs = $elm.attr("sdc_".concat(ev_type));
    if (attrs) {
      if (!controller) {
        controller = (0, _sdc_view.getController)($elm);
        if (!controller) return;
      }
      while (controller) {
        attrs.split(' ').forEach(function (attr) {
          if (is_done) return;
          var handler = null;
          if (typeof attr === 'function') {
            handler = attr;
          } else if (typeof controller[attr] === 'function') {
            handler = controller[attr];
          } else if (typeof attr === 'string' && attr.startsWith('this.event_')) {
            handler = controller.getEvents()[ev_type];
            if (!handler) {
              return;
            }
            handler = handler[attr.slice('this.event_'.length)];
            if (!handler) {
              return;
            }
          }
          handler && handler.call(controller, $elm, event);
        });
        if (is_last_elem) return;
        controller = controller._parentController;
      }
    }
    if (is_done) return;
    $elm = $elm.parent();
  }
  return {
    res: true
  };
}

/**
 *
 */
function initEvents() {
  var $window = $(window);
  STD_EVENT_LIST.forEach(function (ev_type) {
    $window.on(ev_type, windowEventHandler);
  });
}

/**
 *
 * @param {AbstractSDC} controller
 */
function setControllerEvents(controller) {
  if (controller.isEventsSet) {
    return;
  }
  var events = controller.getEvents();
  var _loop = function _loop(ev_type) {
    if (events.hasOwnProperty(ev_type)) {
      var eventList = events[ev_type];
      var _loop2 = function _loop2(domSelector) {
        if (eventList.hasOwnProperty(domSelector)) {
          controller.find(domSelector).each(function () {
            var $elements = $(this);
            var event_list = $elements.attr("sdc_".concat(ev_type)) || null;
            if (!event_list) event_list = [];else event_list = event_list.split(' ');
            var new_key = "this.event_".concat(domSelector);
            if (event_list.indexOf(new_key) === -1) {
              event_list.push(new_key);
              $elements.attr("sdc_".concat(ev_type), event_list.join(' '));
            }
          });
        }
      };
      for (var domSelector in eventList) {
        _loop2(domSelector);
      }
    }
  };
  for (var ev_type in events) {
    _loop(ev_type);
  }

  //controller.isEventsSet = true;
}