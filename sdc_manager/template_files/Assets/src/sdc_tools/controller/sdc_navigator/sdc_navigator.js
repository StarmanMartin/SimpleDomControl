import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {on, trigger} from "../../../simpleDomControl/sdc_events";
import {checkIfParamNumberBoolOrString} from "../../../simpleDomControl/sdc_utils";

import {Modal} from 'bootstrap'

const SDC_SUB_DETAIL_CONTROLLER = 'sdc_sub_detail_container';
const SDC_DETAIL_CONTROLLER = 'sdc_detail_view';


class SdcNavigatorController extends AbstractSDC {


    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/sdc_navigator"; //<sdc-navigator></sdc-navigator>

        this._history_path = [];
        this._history_idx = 0;
        this._origin_target = [];
        this._$detail_view_container = [];
        this._default_controller = null;
        this._previous_args = [];

        this._non_controller_path_prefix = '/';
        this._menu_id = 0;

        /**
         * Events is an array of dom events.
         * The pattern is {'event': {'dom_selector': handler}}
         * Uncommend the following line to add events;
         */
        this.events.unshift({'click': {
            '.navigation-links': function(btn, ev) { this.onNavLink(btn, ev); }
        }});
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - onRefresh  (recalled on reload)              //
    //-------------------------------------------------//
    // - onRemove                                      //
    //-------------------------------------------------//

    onInit(defaultController) {
        this._default_controller = defaultController;
    }

    onLoad($html) {
        on('onNavLink', this);
        on('onNavigateToController', this);
        on('changeMenu', this);
        on('navigateToPage', this);
        on('navLoaded', this);
        on('login', this);
        on('logout', this);

        let temp = this.$container.html();
        $html.find('.main-nav-import-container').append(this.$container.html());
        return super.onLoad($html);
    }

    willShow() {
        let self = this;
        $(window).resize(function () {
            trigger('_onResize', self);
        });
        this._setupButton();
        let data = this._handleUrl(window.location.pathname);
        let $button = this._updateButton(data.buttonSelector);
        history.pushState(data.contentName, $button, data.url);
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    get default_controller() {
        if (!this._default_controller) {
            console.error(`Set data-default-controller in the < ${this.tagName}> (tag name of the default controller)`);
            return '';
        }

        return this._default_controller;
    }


    /** Event Handler **/
    onNavLink(btn, ev) {
        if (ev) {
            ev.preventDefault();
        }

        this.onNavigateToController($(btn).attr('href'))
    }

    onNavigateToController(controller_path_as_array, args = null) {
        if (Array.isArray(controller_path_as_array)) {
            controller_path_as_array = controller_path_as_array.join('~')
        }
        if (args) {
            if (Array.isArray(args)) {
                args = args.join('&')
            }
            controller_path_as_array += '~&' + args
        }
        let data = this._handleUrl(controller_path_as_array);
        const $button = this._updateButton(data.buttonSelector);
        history.pushState(data.contentName, $button, data.url);
    }

    navigateToPage(target, args) {
        this._origin_target = target;
        args = this._parseArgs(args);
        this._previous_args = args;

        let viewObj = this._getSubViewObj(this._origin_target);

        if (viewObj.container.container.data('modal')) {
            this._currentModal = new Modal(viewObj.container.empty_container.closest(viewObj.container.container.data('modal'))[0], {
                keyboard: false
            });
            this._currentModal.show();this._currentModal.off = () => {this.addEvent('hide.bs.modal', viewObj.container.container.data('modal'), () => {});};

            this.addEvent('hide.bs.modal', viewObj.container.container.data('modal'), () => {
                this._currentModal.off();
                this.onNavigateToController('..');
            });
        } else if (this._currentModal) {
            this._currentModal.off();
            this._currentModal.hide();
            this._currentModal = null;
        }
        if (viewObj.isBack) {
            viewObj.container.active_sub_container.removeClass('active loading');
            viewObj.container.empty_container.addClass('empty').removeClass('active loading');
            viewObj.container.active_container.addClass('active').removeClass('empty loading');
            viewObj.container.deeper_sub_container.safeEmpty().removeClass('empty loading');
            let controller = app.getController(viewObj.container.active_container.find('> ._sdc_controller_'));
            this._manageDefault(viewObj.container.active_container);
            if (typeof controller.onBack === 'function') {
                controller.onBack();
            }
            return;
        }

        viewObj.container.empty_container.addClass('loading');
        viewObj.container.active_sub_container.addClass('loading');
        viewObj.container.active_container.addClass('loading');

        let $newElement = $(`<${viewObj.target}_sdc-navigation-client></${viewObj.target}_sdc-navigation-client>`);

        for (let key in args) {
            if (args.hasOwnProperty(key)) {
                const data_key = key.replace(
                    /([A-Z])/g,
                    (group) => '-' + group.toLowerCase()
                )
                $newElement.data(data_key, args[key]);
            }
        }
        viewObj.container.empty_container.safeEmpty().append($newElement);

        this.refresh();
        this.find('.header-loading').addClass('active');
        if (!$newElement.hasClass("_sdc_controller_")) {
            viewObj.container.empty_container.empty().append(`<sdc-error_sdc-sdc-navigation-client data-code="${404}"></sdc-error_sdc-sdc-navigation-client>`);
            this.refresh();

        }
    }


    navLoaded() {
        let idx = this._history_path.length - 1;
        let last_view_array = this._preparedLastViewContainer(idx);
        last_view_array.active_container.removeClass('active loading').addClass('empty');
        last_view_array.active_sub_container.removeClass('active loading');
        last_view_array.empty_container.addClass('active').removeClass('empty loading');
        last_view_array.deeper_sub_container.safeEmpty().removeClass('empty loading');


        $('.tooltip.fade.show').remove();
        if (this._origin_target.length !== this._history_path.length) {
            let data = this._handleUrl(window.location.pathname);
            if (data.path.length > 1) {
                let $button = this._updateButton(data.buttonSelector);
                history.pushState(data.contentName, $button, data.url);
            }
        } else {
            this._manageDefault(last_view_array.empty_container);
            setTimeout(() => {
                this.$container.find('.header-loading').removeClass('active');
            }, 100);
        }
    }

    /** Private functions **/

    _preparedLastViewContainer() {
        let $container = this._$detail_view_container.at(-1);
        const idx = (this._$detail_view_container.length - 1);
        if ($container.length === 0) console.error(`sdc-navigation only works if you have a <div class="${SDC_DETAIL_CONTROLLER}"></div>`);

        if (!$container.hasClass(`prepared`)) $container.addClass(`prepared`).safeEmpty();
        if (!$container.hasClass(`prepared${idx}`)) {
            $container.addClass(`prepared${idx}`)
                .append(`<div data-nav-idx="${idx}" class="${SDC_SUB_DETAIL_CONTROLLER} ${idx}_${SDC_SUB_DETAIL_CONTROLLER} empty"></div>`)
                .append(`<div data-nav-idx="${idx}" class="${SDC_SUB_DETAIL_CONTROLLER} ${idx}_${SDC_SUB_DETAIL_CONTROLLER} active"></div>`);
        }
        let $active_container = $container.find(`> .${idx}_${SDC_SUB_DETAIL_CONTROLLER}`).eq(1);
        let $empty_container = $container.find(`> .${idx}_${SDC_SUB_DETAIL_CONTROLLER}`).first();
        if(!$empty_container.hasClass('empty')) {
            [$empty_container, $active_container] = [$active_container, $empty_container];
        }
        return {
            container: $container,
            empty_container: $empty_container,
            active_container: $active_container,
            active_sub_container: $container.find(`.${SDC_SUB_DETAIL_CONTROLLER}.active`).filter(function () {
                return parseInt($(this).data('nav-idx')) !== idx;
            }),
            deeper_sub_container: $container.find(`.${SDC_SUB_DETAIL_CONTROLLER}`).filter(function () {
                return parseInt($(this).data('nav-idx')) > idx;
            })
        };
    }

    _getViewContainer(idx = 0) {

        if (this._$detail_view_container.length === 0) {
            this._$detail_view_container.push(this.find(`.${SDC_DETAIL_CONTROLLER}`));
        }

        this._$detail_view_container.splice(idx + 1).map($x => $x.addClass('sdc_nav_to_remove').find(`> .${SDC_SUB_DETAIL_CONTROLLER}`).addClass('loading'));
        let $last_detail_container = this._preparedLastViewContainer();

        if (this._$detail_view_container.length !== idx + 1) {
            let $next_detail_view = $last_detail_container.active_container.find(`.${SDC_DETAIL_CONTROLLER}`);
            if ($next_detail_view.length !== 0) {
                this._$detail_view_container.push($next_detail_view.first());
            } else {
                this._$detail_view_container.push(this._$detail_view_container.at(-1));
            }

            $last_detail_container = this._preparedLastViewContainer();
        }


        return $last_detail_container;
    }

    _getSubViewObj(target) {
        let idx = 0;
        let isBack = false;
        while (idx < Math.min(target.length, this._history_path.length)
        && target[idx] === this._history_path[idx]) {
            idx++;
        }

        if (idx >= target.length && target[idx - 1] === this._history_path[idx - 1]) {
            idx = target.length - 1;
            isBack = target.length < this._history_path.length;
            this._history_path = [...target];
        } else if (idx >= target.length) {
            idx = target.length - 1;
            this._history_path = [...target];
        } else {
            this._history_path = [...target].slice(0, idx + 1);
        }

        let container = this._getViewContainer(idx);

        return {
            idx: idx,
            container: container,
            target: target[idx],
            isBack: isBack
        };
    }

    changeMenu(menu_id) {
        if (menu_id > 0 && this._menu_id !== menu_id) {
            this._menu_id = menu_id;
            this.find('.nav-menu-set').removeClass('active');
            this.find(`.nav-menu-set.menu-${menu_id}`).addClass('active');
        }
    }

    _setupButton() {
        let self = this;
        this.find('.navigation-links:not(._link-done)').each(function () {
            let $button = $(this);
            $button.addClass(`_link-done`);
            if (!this.hasAttribute('href')) {
                return;
            }

            let data = self._handleUrl($button.attr('href'));
            $button.addClass(`nav-family-${data.path.at(-1)}`);
        });
    }

    _updateButton(button_selector) {
        let $button;
        if (button_selector) {
            this._currentButton = button_selector;
        }

        $button = this.find(this._currentButton.join(', '));


        if ($button) {
            this.find('.navigation-links').removeClass('active');
            $button.addClass('active');
        }

        return $button;
    }

    _handleUrl(location_path_str) {
        if (location_path_str.startsWith('.')) {
            let location_path_args = location_path_str.split('~&');
            let args = location_path_args.length >= 2 ? location_path_args[1] : '';
            let path_array = location_path_args[0].split(/[~/]/);
            let last_path_array = [...this._history_path];

            for (let path_elem of path_array) {
                if (path_elem === '..') {
                    last_path_array.pop();
                } else if (path_elem !== '.' && path_elem !== '') {
                    last_path_array.push(path_elem);
                }
            }
            location_path_str = this._non_controller_path_prefix + "~" + last_path_array.join('~');
            args = this._parseArgs(args);
            let all_args = []

            for (const [key, value] of Object.entries(this._previous_args)) {
                if (!args.hasOwnProperty(key)) {
                    args[key] = value;
                }
            }
            for (const [key, value] of Object.entries(args)) {
                all_args.push(`${key}=${value}`);
            }
            if (all_args.length > 0) {
                location_path_str += '~&' + all_args.join('&');
            }

        }

        let url = `${window.location.protocol}//${window.location.host}${location_path_str}`;
        if (location_path_str) {
            this._non_controller_path_prefix = location_path_str.split('~')[0];
            location_path_str = location_path_str.replace(/^[^~]+~?|\/+$/gm, '');
        }

        if (!location_path_str || location_path_str.length === 0) {
            location_path_str = `${this.default_controller}`;
        }


        let pathname = location_path_str.split('~&') || [`/~${this.default_controller}`];
        let path = pathname[0].split('~');

        let button_selector = path.map((c) => `.navigation-links.nav-family-${c}`);

        return {
            contentName: location_path_str,
            path: path,
            buttonSelector: button_selector,
            url: url
        }

    }

    _parseArgs(args) {
        if (!args || args === '') {
            return {}
        }
        let route_args = {};
        let route_args_temp = args.split('&');
        for (var i = 0; i < route_args_temp.length; i++) {
            let keyValue = route_args_temp[i].split('=');
            let key = keyValue.shift();
            let value = keyValue.join('=');
            if (route_args.hasOwnProperty(key)) {
                console.error("Duplication of url params: " + key)
            }

            route_args[key] = checkIfParamNumberBoolOrString(decodeURIComponent(value));
        }

        return route_args;
    }

    _manageDefault(container) {
        const $sub_container = container.find(`.${SDC_DETAIL_CONTROLLER}`);
        const df = $sub_container.data('default-controller');
        if (df) {
            let data = this._handleUrl(`.~${df}`);
            const $button = this._updateButton(data.buttonSelector);
            history.pushState(data.contentName, $button, data.url);
        }
    }

    login(pk) {
        for (let i in this._childController) {
            if (this._childController.hasOwnProperty(i)) {
                for (let cc of this._childController[i]) {
                    app.reloadController(cc);
                }
            }
        }
    }

    logout(pk) {
        this.login(pk);
    }

}

app.register(SdcNavigatorController);


(function (history) {
    function updateStateFunc(state_function_name) {
        let state_function = history[state_function_name];
        history[state_function_name] = function (state, $button, urlNew) {
            let state_args = Array.apply(null, arguments);
            if (typeof history['on' + state_function_name.toLowerCase()] === "function") {
                history['on' + state_function_name.toLowerCase()]({state: state});
            }

            state = state.split('~&');

            let route_args = state.length > 1 ? state[1] : "";


            let path_array = state[0].replace(/^~/, '');
            path_array = path_array.split('~').map((x) => `${x}`);

            if ($button) {
                state_args[1] = $button.text();
            } else {
                state_args[1] = "";
            }

            trigger.apply(app.events, ['navigateToPage', path_array].concat(route_args));
            if (typeof state_function !== 'function') {
                return;
            }

            return state_function.apply(history, state_args);
        };
    }

    updateStateFunc('replaceState');
    updateStateFunc('pushState');
    updateStateFunc('popState');

    window.onpopstate = function (event) {
        history.popState(event.state);
    };
})(window.history);