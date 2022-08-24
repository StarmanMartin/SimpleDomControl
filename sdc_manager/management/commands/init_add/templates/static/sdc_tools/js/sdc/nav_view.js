import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {checkIfParamNumberBoolOrString} from '../../../simpleDomControl/sdc_utils.js';
import {on, trigger} from "../../../simpleDomControl/sdc_events.js";


const SUP_CONTAINER = 'sub-page-container';
const CONTAINER = 'div-page-container';

class NavViewController extends AbstractSDC {
    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/nav_view"; //<nav-view></nav-view>
        this._cssUrls.push('/static/sdc_tools/css/sdc/nav_view.css');

        this.menu_id = 1;
        this._containerSelector = CONTAINER;
        this.contentReload = true;


        this._lastSuperSiew = "";
        this._defaultController = null;
        this._currentButton = null;

        this._$view_container = [];
        this._view_container_idx = [];
        this._last_view = [];

        this.events.unshift({
            'click': {
                '.navigation-links': this.onNavLink
            }
        });
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - afterShow  (recalled on reload)               //
    //-------------------------------------------------//
    // - onRemove                                      //
    //-------------------------------------------------//

    onRefresh() {
        this.setupButton();
        this.updateButton();
        return super.onRefresh();
    }

    onInit(defaultController) {
        this._defaultController = defaultController;
    }

    onLoad($html) {

        on('onNavLink', this);
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

        this.setupButton();
        let data = this.handleUrl(window.location.pathname);
        let $button = this.updateButton(data.buttonSelector);
        history.pushState(data.contentName, $button, data.url);
        return super.willShow();
    }

    afterShow() {
        return super.afterShow();
    }

    setupButton() {
        let self = this;
        this.find('.navigation-links:not(._link-done)').each(function () {
            let $button = $(this);
            $button.addClass(`_link-done`);
            if (this.hasAttribute('data-content-name')) {
                $button.attr('href', $button.data('content-name'));
            }

            let data = self.handleUrl($button.attr('href'));
            $button.addClass(`nav-family-${data.path[0]}`);
        });
    }

    get defaultController() {
        if (!this._defaultController) {
            console.error(`Set this._defaultController in ${this.tagName} (tag name of the default controller)`);
            return '';
        }

        return this._defaultController;
    }

    changeMenu(menu_id) {
        if (menu_id > 0 && this.menu_id !== menu_id) {
            this.menu_id = menu_id;
            this.find('.nav-menu-set').removeClass('active');
            this.find(`.nav-menu-set.menu-${menu_id}`).addClass('active');
        }
    }

    onNavLink(btn, ev) {
        if (ev) {
            ev.preventDefault();
        }
        let $button = $(btn);

        let data = this.handleUrl($button.attr('href'));
        this.updateButton(data.buttonSelector);
        history.pushState(data.contentName, $button, data.url);
    }

    updateButton(button_selector) {
        let $button;
        if (button_selector) {
            this._currentButton = button_selector;
            $button = this.find(button_selector);
        } else {
            $button = this.find(this._currentButton);
        }

        if ($button) {
            this.find('.navigation-links').removeClass('active');
            $button.addClass('active');
        }

        return $button;
    }

    handleUrl(totalPathName) {
        let url = `${window.location.protocol}//${window.location.host}${totalPathName}`;
        if (totalPathName) {
            totalPathName = totalPathName.replace(/^[^~]+~?|\/+$/gm, '');
        }

        if (!totalPathName || totalPathName.length === 0) {
            totalPathName = `${this.defaultController}`;
        }


        let pathname = totalPathName.split('~&') || [`/~${this.defaultController}`];
        let path = pathname[0].split('~');


        let contentName = path[0];
        let buttonSelector = `.navigation-links.nav-family-${contentName}`;


        return {
            contentName: totalPathName,
            path: path,
            buttonSelector: buttonSelector,
            url: url
        }

    }

    _getViewContainer(idx = 0) {
        if (this._$view_container.length === 0) {
            this._$view_container = [[
                this.find(`.${CONTAINER}.active`),
                this.find(`.${CONTAINER}.empty`)
            ]];

        }

        this._$view_container.splice(idx + 1);

        if (this._$view_container.length !== idx + 1) {
            let $last_container = this._$view_container.at(-1)[0];
            let $subpage = $last_container.find(`.${SUP_CONTAINER}`);
            let nav_layer = this._$view_container.length
            if ($subpage.length > 0 && !$subpage.hasClass('prepared')) {
                $subpage.addClass(`empty ${SUP_CONTAINER}-${nav_layer}`);
                let $ce = $(`<div class="${SUP_CONTAINER} ${SUP_CONTAINER}-${nav_layer} prepared active">`);
                $ce.insertAfter($subpage);
                this._$view_container.push([
                    $subpage,
                    $ce
                ]);
            } else if ($subpage.length > 0) {
                this._$view_container.push([
                    $subpage.filter(`.${SUP_CONTAINER}-${nav_layer}.active`),
                    $subpage.filter(`.${SUP_CONTAINER}-${nav_layer}.empty`),
                ]);
            } else {
                let a = [
                    this._$view_container.at(-1)[0],
                    this._$view_container.at(-1)[1]
                ];
                a.notReverse = true;
                this._$view_container.push(a);
            }
        }

        let returnObj = this._$view_container.at(-1);
        returnObj.update = function () {
            this[0].removeClass('active loading').addClass('empty');
            this[1].addClass('active').removeClass('empty loading');
            if (!this.notReverse) {
                this.reverse();
            }
        }.bind(returnObj);
        return returnObj;
    }

    _getSubViewObj(target) {
        let idx = 0;
        let isBack = false;
        while (idx < Math.min(target.length, this._last_view.length)
        && target[idx] === this._last_view[idx]) {
            idx++;
        }

        if (idx >= target.length && target[idx - 1] === this._last_view[idx - 1]) {
            idx = target.length - 1;
            isBack = target.length < this._last_view.length;
            this._last_view = target;
        } else if (idx >= target.length) {
            idx = target.length - 1;
            this._last_view = target;
        } else {
            this._last_view = target.slice(0, idx + 1);
        }

        let container = this._getViewContainer(idx);

        return {
            idx: idx,
            container: container,
            target: target[idx],
            isBack: isBack
        };
    }


    navigateToPage(target, args) {
        let argsAsString = "";
        this._originTArget = target;

        for (let key in args) {
            if (args.hasOwnProperty(key)) {
                argsAsString += " data-" + key.replace(
                    /([A-Z])/g,
                    (group) => '-' + group.toLowerCase()
                ) + '="' + args[key] + '"';
            }
        }

        let viewObj = this._getSubViewObj(target);
        if (viewObj.isBack) {
            viewObj.container[1].removeClass('active loading').addClass('empty');
            viewObj.container[0].addClass('active').removeClass('empty loading');
            let controller = app.getController(viewObj.container[0].find(' > ._sdc_controller_'));
            if (typeof controller.onBack === 'function') {
                controller.onBack();
            }
            return;
        }

        viewObj.container[0].addClass('loading');
        viewObj.container[1].addClass('loading');

        let $newElement = $(`<${viewObj.target}${argsAsString}><${viewObj.target}/>`);
        viewObj.container[1].empty().append($newElement);

        app.refresh(viewObj.container[1]);
        this.find('.header-loading').addClass('active');
        if (!$newElement.hasClass("_sdc_controller_")) {
            viewObj.container[1].empty().append(`<error_nav-client data-code="${404}"><error_nav-client/>`);
            app.refresh(viewObj.container[1]);

        }
    }

    navLoaded() {
        let idx = this._last_view.length - 1;
        let ce = this._getViewContainer(idx);
        ce.update();

        $('.tooltip.fade.show').remove();
        if (this._originTArget.length !== this._last_view.length) {
            let data = this.handleUrl(window.location.pathname);
            if (data.path.length > 1) {
                let $button = this.updateButton(data.buttonSelector);
                history.pushState(data.contentName, $button, data.url);
            }
        }
        setTimeout(() => {
            this.$container.find('.header-loading').removeClass('active');
        }, 100);
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
        for (let i in this._childController) {
            if (this._childController.hasOwnProperty(i)) {
                for (let cc of this._childController[i]) {
                    app.reloadController(cc);
                }
            }
        }
    }

}

app.register(NavViewController);


(function (history) {
    function updateStateFunc(name) {
        let pushState = history[name];
        history[name] = function (state, $button, urlNew) {
            let argsPush = Array.apply(null, arguments);
            if (typeof history['on' + name.toLowerCase()] === "function") {
                history['on' + name.toLowerCase()]({state: state});
            }

            state = state.split('~&');

            let routeArgs = {};
            if (state.length > 1) {
                let routeArgsTemp = state[1].split('&');
                for (var i = 0; i < routeArgsTemp.length; i++) {
                    let keyValue = routeArgsTemp[i].split('=');
                    let key = keyValue.shift();
                    let value = keyValue.join('=');
                    if (routeArgs.hasOwnProperty(key)) {
                        console.error("Duplication of url params: " + key)
                    }

                    routeArgs[key] = checkIfParamNumberBoolOrString(decodeURIComponent(value));
                }
            }


            state = state[0].replace(/^~/, '');
            state = state.split('~');
            for (let i = 0; i < state.length; ++i) {
                state[i] = `${state[i]}_nav-client`;
            }

            if ($button) {
                argsPush[1] = $button.text();
            } else {
                argsPush[1] = "";
            }

            trigger.apply(app.events, ['navigateToPage', state].concat(routeArgs));
            if (typeof pushState !== 'function') {
                return;
            }

            return pushState.apply(history, argsPush);
        };
    }

    updateStateFunc('replaceState');
    updateStateFunc('pushState');
    updateStateFunc('popState');

    window.onpopstate = function (event) {
        history.popState(event.state);
    };
})(window.history);