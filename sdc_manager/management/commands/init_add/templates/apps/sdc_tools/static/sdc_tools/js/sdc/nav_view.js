import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';
import {checkIfParamNumberBoolOrString} from '../../../simpleDomControl/sdc_utils.js';
import {on, trigger} from "../../../simpleDomControl/sdc_events.js";



const  SUP_CONTAINER = 'sub-page-container';
const  CONTAINER = 'div-page-container';

class NavViewController extends AbstractSDC {
    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/nav_view"; //<nav-view></nav-view>
        this._cssUrls.push('/static/sdc_tools/css/sdc/nav_view.css');

        this.menu_id = 1;
        this._lastSuperSiew = "";
        this._containerSelector = CONTAINER;
        this._defaultController = null;
        this._currentButton = null;
        this.contentReload = true;

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
    };

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
        if(totalPathName) {
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

    };


    navigateToPage(target, args) {
        let argsAsString = "";
        this.find('.sidebar-nav-left').removeClass('active');
        for (let key in args) {
            if (args.hasOwnProperty(key)) {
                argsAsString += " data-" + key.replace(
                    /([A-Z])/g,
                    (group) => '-' + group.toLowerCase()
                ) + '="' + args[key] + '"';
            }
        }


        let $ce;
        if(target.length > 1 && this._lastSuperSiew === target[0]) {
            this._containerSelector = SUP_CONTAINER;
            let $subpage = this.find(`.${SUP_CONTAINER}`);
            if(!$subpage.hasClass('prepared')) {
                $subpage.addClass('prepared active');
                $ce = $(`<div class="${SUP_CONTAINER} empty">`);
                $ce.insertAfter($subpage);
            } else {
                $ce = $subpage.filter(`.empty`);
            }

        }

        let finalTarget = target[target.length - 1]
        this._lastSuperSiew = target[0]

        if(!$ce || $ce.length === 0) {
            this._containerSelector = CONTAINER;
            $ce = this.find(`.${CONTAINER}.empty`);
            finalTarget = target[0]
        }

        this.find(`.${this._containerSelector}`).addClass('loading');

        let $newElement = $(`<${finalTarget}${argsAsString}><${finalTarget}/>`);
        $ce.empty().append($newElement);

        app.refresh($ce);
        this.find('.header-loading').addClass('active');
    };

    navLoaded(controller) {
        let $ca = this.find(`.${this._containerSelector}.active`);
        let $ce = this.find(`.${this._containerSelector}.empty`);
        $ca.removeClass('active loading').addClass('empty');
        $ce.addClass('active').removeClass('empty loading');
        app.safeEmpty($ca);
        if(controller.hasSubnavView) {
            let data = this.handleUrl(window.location.pathname);
            if(data.path.length > 1) {
                let $button = this.updateButton(data.buttonSelector);
                history.pushState(data.contentName, $button, data.url);
            }
        }
        setTimeout(() => {
            this.$container.find('.header-loading').removeClass('active');
        }, 100);
    };

    login (pk) {
        for (let i in this._childController) {
            if (this._childController.hasOwnProperty(i)) {
                for (let cc of this._childController[i]) {
                    app.reloadController(cc);
                }
            }
        }
    }

    logout (pk) {
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
            for(let i = 0; i < state.length; ++i) {
                state[i] = `${state[i]}_nav-client`;
            }

            if ($button) {
                argsPush[1] = $button.text();
            } else {
                argsPush[1] = "";
            }


            trigger.apply(app.events, ['navigateToPage', state].concat(routeArgs));

            return pushState.apply(history, argsPush);
        };
    }

    updateStateFunc('replaceState');
    updateStateFunc('pushState');

    window.onpopstate = function (event) {
        history.pushState(event.state);
        return true;
    };
})(window.history);