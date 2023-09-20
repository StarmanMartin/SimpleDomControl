"use strict";

function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.Model = void 0;
exports.callServer = callServer;
exports.isConnected = isConnected;
var _sdc_main = require("./sdc_main.js");
var _sdc_events = require("./sdc_events.js");
var _sdc_utils = require("./sdc_utils");
function _createForOfIteratorHelper(o, allowArrayLike) { var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"]; if (!it) { if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") { if (it) o = it; var i = 0; var F = function F() {}; return { s: F, n: function n() { if (i >= o.length) return { done: true }; return { done: false, value: o[i++] }; }, e: function e(_e) { throw _e; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var normalCompletion = true, didErr = false, err; return { s: function s() { it = it.call(o); }, n: function n() { var step = it.next(); normalCompletion = step.done; return step; }, e: function e(_e2) { didErr = true; err = _e2; }, f: function f() { try { if (!normalCompletion && it["return"] != null) it["return"](); } finally { if (didErr) throw err; } } }; }
function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }
function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, _toPropertyKey(descriptor.key), descriptor); } }
function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); Object.defineProperty(Constructor, "prototype", { writable: false }); return Constructor; }
function _toPropertyKey(arg) { var key = _toPrimitive(arg, "string"); return _typeof(key) === "symbol" ? key : String(key); }
function _toPrimitive(input, hint) { if (_typeof(input) !== "object" || input === null) return input; var prim = input[Symbol.toPrimitive]; if (prim !== undefined) { var res = prim.call(input, hint || "default"); if (_typeof(res) !== "object") return res; throw new TypeError("@@toPrimitive must return a primitive value."); } return (hint === "string" ? String : Number)(input); }
function _slicedToArray(arr, i) { return _arrayWithHoles(arr) || _iterableToArrayLimit(arr, i) || _unsupportedIterableToArray(arr, i) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }
function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i]; return arr2; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(arr) { if (Array.isArray(arr)) return arr; }
var IS_CONNECTED = false;
var IS_CONNECTING = false;
var SDC_SOCKET = null;
var MAX_FILE_UPLOAD = 25000;
var OPEN_REQUESTS = {};
function callServer(app, controller, funcName, args) {
  var id = (0, _sdc_utils.uuidv4)();
  isConnected().then(function () {
    SDC_SOCKET.send(JSON.stringify({
      event: 'sdc_call',
      id: id,
      controller: controller,
      app: app,
      "function": funcName,
      args: args
    }));
  });
  return new Promise(function (resolve, reject) {
    OPEN_REQUESTS[id] = [resolve, reject];
  });
}
function _connect() {
  IS_CONNECTING = true;
  return new Promise(function (resolve) {
    if (window.location.protocol === "https:") {
      SDC_SOCKET = new WebSocket("wss://".concat(window.location.host, "/sdc_ws/ws/"));
    } else {
      SDC_SOCKET = new WebSocket("ws://".concat(window.location.host, "/sdc_ws/ws/"));
    }
    SDC_SOCKET.onmessage = function (e) {
      var data = JSON.parse(e.data);
      if (data.is_error) {
        if (_sdc_main.app.Global.sdcAlertMessenger && (data.msg || data.header)) {
          _sdc_main.app.Global.sdcAlertMessenger.pushErrorMsg(data.header || '', data.msg || '');
        }
        if (OPEN_REQUESTS[data.id]) {
          OPEN_REQUESTS[data.id][1](data.data);
          delete OPEN_REQUESTS[data.id];
        }
      } else {
        if (_sdc_main.app.Global.sdcAlertMessenger && (data.msg || data.header)) {
          _sdc_main.app.Global.sdcAlertMessenger.pushMsg(data.header || '', data.msg || '');
        }
        if (data.type && data.type === 'sdc_recall') {
          if (OPEN_REQUESTS[data.id]) {
            OPEN_REQUESTS[data.id][0](data.data);
            delete OPEN_REQUESTS[data.id];
          }
        } else if (data.type && data.type === 'sdc_event') {
          var event = data.event;
          if (event) {
            (0, _sdc_events.trigger)(event, data.payload);
          }
        } else if (data.type && data.type === 'sdc_redirect') {
          (0, _sdc_events.trigger)('onNavLink', data.link);
        }
      }
    };
    SDC_SOCKET.onclose = function () {
      console.error('SDC Socket closed unexpectedly');
      IS_CONNECTED = false;
      for (var _i = 0, _Object$entries = Object.entries(OPEN_REQUESTS); _i < _Object$entries.length; _i++) {
        var _Object$entries$_i = _slicedToArray(_Object$entries[_i], 2),
          key = _Object$entries$_i[0],
          value = _Object$entries$_i[1];
        value[1]({});
        delete OPEN_REQUESTS[key];
      }
      setTimeout(function () {
        _connect();
      }, 1000);
    };
    SDC_SOCKET.onerror = function (err) {
      console.error('Socket encountered error: ', err.message, 'Closing socket');
      if (IS_CONNECTED) {
        try {
          SDC_SOCKET.close();
        } catch (e) {}
      }
    };
    SDC_SOCKET.onopen = function () {
      IS_CONNECTED = true;
      IS_CONNECTING = false;
      resolve();
    };
  });
}
function close() {
  if (IS_CONNECTED) {
    IS_CONNECTED = false;
    try {
      SDC_SOCKET.close();
    } catch (e) {}
  }
}
function parse_hidden_inputs(value) {
  var isFloatReg = /^-?\d+\.?\d+$/;
  var isIntReg = /^-?\d+$/;
  var isBoolReg = /^(true|false)$/;
  var isStringReg = /^(['][^']*['])|(["][^"]*["])$/;
  if (value.toLowerCase().match(isBoolReg)) {
    return value.toLowerCase() === 'true';
  } else if (value === 'undefined') {
    return undefined;
  } else if (value.toLowerCase() === 'none') {
    return null;
  } else if (value.match(isIntReg)) {
    return parseInt(value);
  } else if (value.match(isFloatReg)) {
    return parseFloat(value);
  } else if (value.match(isStringReg)) {
    return value.substring(1, value.length - 1);
  }
  return value;
}
function isConnected() {
  return new Promise(function (resolve) {
    if (IS_CONNECTED) {
      return resolve();
    } else if (IS_CONNECTING) {
      setTimeout(function () {
        isConnected().then(function () {
          resolve();
        });
      }, 200);
    } else {
      return resolve(_connect());
    }
  });
}
var Model = /*#__PURE__*/function (_Symbol$iterator) {
  /**
   *
   * @param model_name {string}
   * @param model_query {json}
   */
  function Model(model_name) {
    var model_query = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
    _classCallCheck(this, Model);
    this.values_list = [];
    this.values = {};
    this.model_name = model_name;
    this.model_query = model_query;
    this._is_connected = false;
    this._is_conneting_process = false;
    this._auto_reconnect = true;
    this.socket = null;
    this.open_request = {};
    this.on_update = function () {};
    this.on_create = function () {};
    this.form_id = (0, _sdc_utils.uuidv4)();
  }
  _createClass(Model, [{
    key: _Symbol$iterator,
    value: function value() {
      var idx = 0;
      return {
        next: function next() {
          if (idx < this.values_list) {
            ++idx;
            return {
              value: this.values_list[idx],
              done: false
            };
          }
          return {
            value: null,
            done: true
          };
        }
      };
    }
  }, {
    key: "byPk",
    value: function byPk(pk) {
      if (pk !== null) {
        var elem = this.values_list.find(function (elm) {
          return elm.pk === pk;
        });
        if (!elem) {
          elem = {
            pk: pk
          };
          this.values_list.push(elem);
        }
        return elem;
      }
      return {
        pk: pk
      };
    }
  }, {
    key: "filter",
    value: function filter(model_query) {
      this.model_query = Object.assign({}, this.model_query, model_query);
      return this;
    }
  }, {
    key: "load",
    value: function load() {
      var _this = this;
      return this.isConnected().then(function () {
        var id = (0, _sdc_utils.uuidv4)();
        return new Promise(function (resolve, reject) {
          _this.socket.send(JSON.stringify({
            event: 'model',
            event_type: 'load',
            event_id: id,
            args: {
              model_name: _this.model_name,
              model_query: _this.model_query
            }
          }));
          _this.open_request[id] = [resolve, reject];
        });
      });
    }
  }, {
    key: "listView",
    value: function listView() {
      var _this2 = this;
      var filter = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
      var cb_resolve = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
      var cb_reject = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var $div_list = $('<div class="container-fluid">');
      this.isConnected().then(function () {
        var id = (0, _sdc_utils.uuidv4)();
        new Promise(function (resolve, reject) {
          _this2.socket.send(JSON.stringify({
            event: 'model',
            event_type: 'list_view',
            event_id: id,
            args: {
              model_name: _this2.model_name,
              model_query: _this2.model_query,
              filter: filter
            }
          }));
          _this2.open_request[id] = [function (data) {
            $div_list.append(data.html);
            _sdc_main.app.refresh($div_list);
            cb_resolve && cb_resolve(data);
            resolve(data);
          }, function (res) {
            cb_reject && cb_reject(res);
            reject(res);
          }];
        });
      });
      return $div_list;
    }
  }, {
    key: "detailView",
    value: function detailView() {
      var _this3 = this;
      var pk = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : -1;
      var cb_resolve = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
      var cb_reject = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var $div_list = $('<div class="container-fluid">');
      var load_promise;
      if (this.values_list.length !== 0) {
        load_promise = this.isConnected();
      } else {
        load_promise = this.load();
      }
      load_promise.then(function () {
        if (pk === -1) {
          pk = _this3.values_list[0].pk;
        }
        var id = (0, _sdc_utils.uuidv4)();
        new Promise(function (resolve, reject) {
          _this3.socket.send(JSON.stringify({
            event: 'model',
            event_type: 'detail_view',
            event_id: id,
            args: {
              model_name: _this3.model_name,
              model_query: _this3.model_query,
              pk: pk
            }
          }));
          _this3.open_request[id] = [function (data) {
            $div_list.append(data.html);
            _sdc_main.app.refresh($div_list);
            cb_resolve && cb_resolve(data);
            resolve(data);
          }, function (res) {
            cb_reject && cb_reject(res);
            reject(res);
          }];
        });
      });
      return $div_list;
    }
  }, {
    key: "syncFormToModel",
    value: function syncFormToModel($forms) {
      return this.syncForm($forms);
    }
  }, {
    key: "syncModelToForm",
    value: function syncModelToForm($forms) {
      if (!$forms || !$forms.hasClass(this.form_id)) {
        $forms = $(".".concat(this.form_id));
      }
      var self = this;
      $forms.each(function () {
        if (!this.hasAttribute('data-model_pk')) {
          return;
        }
        var pk = $(this).data('model_pk');
        var instance = self.byPk(pk);
        var _iterator = _createForOfIteratorHelper(this.elements),
          _step;
        try {
          for (_iterator.s(); !(_step = _iterator.n()).done;) {
            var form_item = _step.value;
            var name = form_item.name;
            if (name && name !== '') {
              if (form_item.type === 'checkbox') {
                form_item.checked = instance[name];
              } else if (form_item.type === 'file' && instance[name] instanceof File) {
                var container = new DataTransfer();
                container.items.add(file);
                form_item.files = container;
              } else {
                $(form_item).val(instance[name]);
              }
            }
          }
        } catch (err) {
          _iterator.e(err);
        } finally {
          _iterator.f();
        }
      });
    }
  }, {
    key: "syncForm",
    value: function syncForm($forms) {
      if (!$forms || !$forms.hasClass(this.form_id)) {
        $forms = $(".".concat(this.form_id));
      }
      var self = this;
      var instances = [];
      $forms.each(function () {
        var $form = $(this);
        var pk = $form.data('model_pk');
        var instance = self.byPk(pk);
        var _iterator2 = _createForOfIteratorHelper(this.elements),
          _step2;
        try {
          for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
            var form_item = _step2.value;
            var name = form_item.name;
            if (name && name !== '') {
              if (form_item.type === 'hidden') {
                instance[name] = parse_hidden_inputs($(form_item).val());
              } else if (form_item.type === 'checkbox') {
                instance[name] = form_item.checked;
              } else if (form_item.type === 'file') {
                instance[name] = form_item.files[0];
              } else {
                instance[name] = $(form_item).val();
              }
            }
          }
        } catch (err) {
          _iterator2.e(err);
        } finally {
          _iterator2.f();
        }
        instances.push(instance);
        return instance;
      });
      if (this.values_list.length <= 1 && instances.length > 0) {
        this.values = instances.at(-1);
      }
      return instances;
    }
  }, {
    key: "createForm",
    value: function createForm() {
      var _this4 = this;
      var cb_resolve = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : null;
      var cb_reject = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
      var $div_form = $('<div class="container-fluid">');
      this.isConnected().then(function () {
        var id = (0, _sdc_utils.uuidv4)();
        new Promise(function (resolve, reject) {
          _this4.socket.send(JSON.stringify({
            event: 'model',
            event_type: 'create_form',
            event_id: id,
            args: {
              model_name: _this4.model_name,
              model_query: _this4.model_query
            }
          }));
          _this4.open_request[id] = [function (data) {
            $div_form.append(data.html);
            var $form = $div_form.closest('form').addClass("sdc-model-create-form sdc-model-form ".concat(_this4.form_id)).data('model', _this4).data('model_pk', null);
            if (!$form[0].hasAttribute('sdc_submit')) {
              $form.attr('sdc_submit', 'submitModelForm');
            }
            _sdc_main.app.refresh($div_form);
            cb_resolve && cb_resolve(data);
            resolve(data);
          }, function (res) {
            cb_reject && cb_reject(res);
            reject(res);
          }];
        });
      });
      return $div_form;
    }
  }, {
    key: "editForm",
    value: function editForm() {
      var _this5 = this;
      var pk = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : -1;
      var cb_resolve = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
      var cb_reject = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var load_promise;
      if (this.values_list.length !== 0) {
        load_promise = this.isConnected();
      } else {
        load_promise = this.load();
      }
      var $div_form = $('<div  class="container-fluid">');
      load_promise.then(function () {
        if (pk <= -1) {
          pk = _this5.values_list.at(pk).pk;
        }
        var id = (0, _sdc_utils.uuidv4)();
        new Promise(function (resolve, reject) {
          _this5.socket.send(JSON.stringify({
            event: 'model',
            event_type: 'edit_form',
            event_id: id,
            args: {
              model_name: _this5.model_name,
              model_query: _this5.model_query,
              pk: pk
            }
          }));
          _this5.open_request[id] = [function (data) {
            $div_form.append(data.html);
            var $form = $div_form.closest('form').addClass("sdc-model-edit-form sdc-model-form ".concat(_this5.form_id)).data('model', _this5).data('model_pk', pk);
            if (!$form[0].hasAttribute('sdc_submit')) {
              $form.attr('sdc_submit', 'submitModelForm');
            }
            _sdc_main.app.refresh($div_form);
            cb_resolve && cb_resolve(data);
            resolve(data);
          }, function (res) {
            cb_reject && cb_reject(res);
            reject(res);
          }];
        });
      });
      return $div_form;
    }
  }, {
    key: "new",
    value: function _new() {
      var _this6 = this;
      return new Promise(function (resolve, reject) {
        var $form = $('<form>').append(_this6.createForm(function () {
          _this6.syncFormToModel($form);
          resolve();
        }, reject));
      });
    }
  }, {
    key: "save",
    value: function save() {
      var _this7 = this;
      var pk = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : -1;
      return this.isConnected().then(function () {
        var elem_list;
        if (pk > -1) {
          elem_list = [_this7.byPk(pk)];
        } else {
          elem_list = _this7.values_list;
        }
        var p_list = [];
        elem_list.forEach(function (elem) {
          var id = (0, _sdc_utils.uuidv4)();
          p_list.push(new Promise(function (resolve, reject) {
            _this7.socket.send(JSON.stringify({
              event: 'model',
              event_type: 'save',
              event_id: id,
              args: {
                model_name: _this7.model_name,
                model_query: _this7.model_query,
                data: elem
              }
            }));
            _this7.open_request[id] = [function (res) {
              var data = JSON.parse(res.data.instance);
              _this7._parseServerRes(data);
              resolve(res);
            }, reject];
          }));
        });
        return Promise.all(p_list);
      });
    }
  }, {
    key: "create",
    value: function create() {
      var _this8 = this;
      var values = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : this.values;
      var id = (0, _sdc_utils.uuidv4)();
      return this.isConnected().then(function () {
        return new Promise(function (resolve, reject) {
          _this8._readFiles(values).then(function (files) {
            _this8.socket.send(JSON.stringify({
              event: 'model',
              event_type: 'create',
              event_id: id,
              args: {
                model_name: _this8.model_name,
                model_query: _this8.model_query,
                data: values,
                files: files
              }
            }));
            _this8.open_request[id] = [function (res) {
              var data = JSON.parse(res.data.instance);
              _this8._parseServerRes(data);
              resolve(res);
            }, reject];
          });
        });
      });
    }
  }, {
    key: "delete",
    value: function _delete() {
      var _this$values,
        _this9 = this;
      var pk = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : -1;
      if (pk === -1) pk = (_this$values = this.values) === null || _this$values === void 0 ? void 0 : _this$values.pk;
      var id = (0, _sdc_utils.uuidv4)();
      return this.isConnected().then(function () {
        return new Promise(function (resolve, reject) {
          _this9.socket.send(JSON.stringify({
            event: 'model',
            event_type: 'delete',
            event_id: id,
            args: {
              model_name: _this9.model_name,
              model_query: _this9.model_query,
              pk: pk
            }
          }));
          _this9.open_request[id] = [resolve, reject];
        });
      });
    }
  }, {
    key: "isConnected",
    value: function isConnected() {
      var _this10 = this;
      return new Promise(function (resolve, reject) {
        if (_this10._is_connected) {
          resolve();
        } else if (!_this10._is_conneting_process) {
          _this10._is_conneting_process = true;
          _this10.open_request['_connecting_process'] = [function () {}, function () {}];
          _this10._connectToServer().then(function () {
            resolve(_this10._checkConnection());
          });
        } else {
          var _this10$open_request$ = _slicedToArray(_this10.open_request['_connecting_process'], 2),
            resolve_origin = _this10$open_request$[0],
            reject_origin = _this10$open_request$[1];
          _this10.open_request['_connecting_process'] = [function () {
            resolve_origin();
            resolve();
          }, function () {
            reject_origin();
            reject();
          }];
        }
      });
    }
  }, {
    key: "close",
    value: function close() {
      if (this.socket) {
        this._auto_reconnect = false;
        this.socket.onclose = function () {};
        this.socket.close();
        delete this['socket'];
      }
    }
  }, {
    key: "_readFiles",
    value: function _readFiles(elem) {
      var _this11 = this;
      var to_solve = [];
      var files = {};
      var _loop = function _loop() {
        var _Object$entries2$_i = _slicedToArray(_Object$entries2[_i2], 2),
          key = _Object$entries2$_i[0],
          value = _Object$entries2$_i[1];
        if (value instanceof File) {
          to_solve.push(new Promise(function (resolve, reject) {
            (function (key, value) {
              var reader = new FileReader();
              reader.onload = function (e) {
                var id = (0, _sdc_utils.uuidv4)();
                _this11.open_request[id] = [resolve, reject];
                var result = e.target.result;
                var number_of_chunks = parseInt(Math.ceil(result.length / MAX_FILE_UPLOAD));
                files[key] = {
                  id: id,
                  file_name: value.name,
                  field_name: key,
                  content_length: value.size
                };
                for (var i = 0; i < number_of_chunks; ++i) {
                  _this11.socket.send(JSON.stringify({
                    event: 'model',
                    event_type: 'upload',
                    event_id: id,
                    args: {
                      chunk: result.slice(MAX_FILE_UPLOAD * i, MAX_FILE_UPLOAD * (i + 1)),
                      idx: i,
                      number_of_chunks: number_of_chunks,
                      file_name: value.name,
                      field_name: key,
                      content_length: value.size,
                      content_type: value.type,
                      model_name: _this11.model_name,
                      model_query: _this11.model_query
                    }
                  }));
                }
              };
              reader.onerror = function () {
                reject();
              };
              reader.readAsBinaryString(value);
            })(key, value);
          }));
        }
      };
      for (var _i2 = 0, _Object$entries2 = Object.entries(elem); _i2 < _Object$entries2.length; _i2++) {
        _loop();
      }
      return Promise.all(to_solve).then(function () {
        return files;
      });
    }
  }, {
    key: "_onMessage",
    value: function _onMessage(e) {
      var data = JSON.parse(e.data);
      if (data.is_error) {
        if (this.open_request.hasOwnProperty(data.event_id)) {
          this.open_request[data.event_id][1](data);
          delete this.open_request[data.event_id];
        }
        if (_sdc_main.app.Global.sdcAlertMessenger && (data.msg || data.header)) {
          _sdc_main.app.Global.sdcAlertMessenger.pushErrorMsg(data.header || '', data.msg || '');
        }
        if (data.type === 'connect') {
          this.open_request['_connecting_process'][1](data);
          delete this.open_request['_connecting_process'];
          this._auto_reconnect = false;
          this.socket.close();
        }
      } else {
        if (_sdc_main.app.Global.sdcAlertMessenger && (data.msg || data.header)) {
          _sdc_main.app.Global.sdcAlertMessenger.pushMsg(data.header || '', data.msg || '');
        }
        if (data.type === 'connect') {
          this._is_connected = true;
          this._is_conneting_process = false;
          this.open_request['_connecting_process'][0](data);
          delete this.open_request['_connecting_process'];
        } else if (data.type === 'load') {
          var json_res = JSON.parse(data.args.data);
          this.values_list = [];
          this._parseServerRes(json_res);
        } else if (data.type === 'on_update' || data.type === 'on_create') {
          var _json_res = JSON.parse(data.args.data);
          var obj = this._parseServerRes(_json_res);
          var cb;
          if (data.type === 'on_create') {
            cb = this.on_create;
          } else {
            cb = this.on_update;
          }
          cb(obj);
        }
        if (this.open_request.hasOwnProperty(data.event_id)) {
          this.open_request[data.event_id][0](data);
          delete this.open_request[data.event_id];
        }
      }
    }
  }, {
    key: "_connectToServer",
    value: function _connectToServer() {
      var _this12 = this;
      return new Promise(function (resolve) {
        var model_identifier = "".concat(_this12.model_name) + (_this12.model_id > 0 ? "/".concat(_this12.model_id) : '');
        if (window.location.protocol === "https:") {
          _this12.socket = new WebSocket("wss://".concat(window.location.host, "/sdc_ws/model/").concat(model_identifier));
        } else {
          _this12.socket = new WebSocket("ws://".concat(window.location.host, "/sdc_ws/model/").concat(model_identifier));
        }
        _this12.socket.onmessage = _this12._onMessage.bind(_this12);
        _this12.socket.onclose = function (e) {
          console.error("SDC Model (".concat(_this12.model_name, ", ").concat(_this12.model_id, ") Socket closed unexpectedly"));
          _this12._is_connected = false;
          for (var _i3 = 0, _Object$entries3 = Object.entries(_this12.open_request); _i3 < _Object$entries3.length; _i3++) {
            var _Object$entries3$_i = _slicedToArray(_Object$entries3[_i3], 2),
              key = _Object$entries3$_i[0],
              value = _Object$entries3$_i[1];
            value[1](e);
          }
          _this12.open_request = {};
          setTimeout(function () {
            if (_this12._auto_reconnect) {
              _this12._connectToServer().then(function () {});
            }
          }, 1000);
        };
        _this12.socket.onerror = function (err) {
          console.error("Model Socket encountered error: ".concat(err, " Closing socket"));
          if (_this12._is_connected) {
            try {
              _this12.socket.close();
            } catch (e) {}
          }
        };
        _this12.socket.onopen = function () {
          resolve();
        };
      });
    }
  }, {
    key: "_checkConnection",
    value: function _checkConnection() {
      var _this13 = this;
      var id = (0, _sdc_utils.uuidv4)();
      return new Promise(function (resolve, reject) {
        _this13.socket.send(JSON.stringify({
          event: 'model',
          event_type: 'connect',
          event_id: id,
          args: {
            model_name: _this13.model_name,
            model_query: _this13.model_query
          }
        }));
        _this13.open_request[id] = [resolve, reject];
      });
    }
  }, {
    key: "_parseServerRes",
    value: function _parseServerRes(res) {
      var updated = [];
      var _iterator3 = _createForOfIteratorHelper(res),
        _step3;
      try {
        for (_iterator3.s(); !(_step3 = _iterator3.n()).done;) {
          var json_data = _step3.value;
          var pk = json_data.pk;
          var obj = this.byPk(pk);
          for (var _i4 = 0, _Object$entries4 = Object.entries(json_data.fields); _i4 < _Object$entries4.length; _i4++) {
            var _Object$entries4$_i = _slicedToArray(_Object$entries4[_i4], 2),
              k = _Object$entries4$_i[0],
              v = _Object$entries4$_i[1];
            //if(v && typeof v === 'object' && v['__is_sdc_model__']) {
            //    obj[k] = new Model(v['model'], {'pk': v['pk']})
            //} else {
            obj[k] = v;
            //}
          }

          updated.push(obj);
        }
      } catch (err) {
        _iterator3.e(err);
      } finally {
        _iterator3.f();
      }
      if (this.values_list.length === 1) {
        this.values = this.values_list.at(-1);
      } else {
        this.values = {};
      }
      return updated;
    }
  }]);
  return Model;
}(Symbol.iterator);
exports.Model = Model;