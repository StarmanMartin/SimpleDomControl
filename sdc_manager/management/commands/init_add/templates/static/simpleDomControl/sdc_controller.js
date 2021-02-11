import {promiseDummyFactory, tagNameToCamelCase, agileAggregation} from "./sdc_utils.js";
import {loadFilesFromController, runControllerFillContent} from "./sdc_view.js";
import {setupEvents} from "./sdc_dom_events.js";
import {runOnInitWithParameter} from "./sdc_params.js";

export let Global = {};
export let controllerList = {};


function prepareMixins(superTagNameList, tagName) {
    superTagNameList = superTagNameList.concat(controllerList[tagName][1]);
    superTagNameList = superTagNameList.filter((value, index, self)=>{
        return self.indexOf(value) === index;
    });
    let hasAdded = true;
    while (hasAdded) {
        hasAdded = false;
        for(let tag of superTagNameList) {
            for(let newTag of controllerList[tag][1]) {
                if(!superTagNameList.includes(newTag)) {
                    superTagNameList.push(newTag);
                    hasAdded = true;
                }
            }
        }
    }
    return superTagNameList;
}

/**
 * setParentController sets the parent controller as property: 'parentController'
 * to the child controller. Also it adds the child controller to the property list:
 * 'parentController' to the parent controller
 *
 * @param {AbstractSDC} parentController - js controller instance, controller of the parent DOM of the controllers DOM
 * @param {AbstractSDC} controller - js controller instance
 * @return {AbstractSDC} - parentController
 */
function setParentController(parentController, controller) {
    if (parentController) {
        let controllerName = tagNameToCamelCase(controller._tagName);
        if (!parentController._childController[controllerName]) {
            parentController._childController[controllerName] = [];
        }

        parentController._childController[controllerName].push(controller);
    }

    return (controller._parentController = parentController)
}
/**
 * controllerFactoryInstance it generates a controller instance
 * depending if the controller is registered as a global controller. It sets the
 * $container object to the jQuery representation of the tag.
 *
 * It handles the init parameter by the data values of the DOM.
 *
 * It handles the super extensions.
 *
 * @param {AbstractSDC} parentController - Controller of the parent DOM
 * @param {jquery} $element - The current DOM jQuery
 * @param {string} tagName - the registered tag name of the current DOM
 * @param {string} superTagNameList - tag names of super controller
 * @return {AbstractSDC} -  new Controller
 */
function controllerFactoryInstance(parentController, $element, tagName, superTagNameList) {

    let mixinControllerClass = [];
    superTagNameList = prepareMixins(superTagNameList, tagName);
    for (let superTagName of superTagNameList) {
        mixinControllerClass.push(controllerList[superTagName][0]);
    }

    let controllerClass = controllerList[tagName][0];
    let controller = new (agileAggregation(controllerClass, ...mixinControllerClass))();
    controller._tagName = tagName;

    setParentController(parentController, controller);
    controller.$container = $element;
    runOnInitWithParameter($element, controller);


    return controller;
}

/**
 * controllerFactory it either generates a controller or takes a globe instance
 * depending if the controller is registered as a global controller. It sets the
 * $container object to the jQuery representation of the tag.
 *
 * Remember Global controller can not have a super controller!
 *
 * @param {AbstractSDC} parentController - Controller of the parent DOM
 * @param {jquery} $element - The current DOM jQuery
 * @param {string} tagName - the registered tag name of the current DOM
 * @param {string} superTagNameList - tag names of super controller
 * @return {AbstractSDC} -  new Controller
 */
export function controllerFactory(parentController, $element, tagName, superTagNameList) {
    let gTagName = tagNameToCamelCase(tagName);
    if (Global[gTagName]) {
        let controller = Global[gTagName];
        setParentController(parentController, controller);
        controller.$container = $element;

        return controller;
    }

    return controllerFactoryInstance(parentController, $element, tagName, superTagNameList);
}

/**
 * runControllerShow first runs onLoad and fill content for all sub
 * controller. Only if all the sub controller are loaded the willShow
 * control flow function gets called.
 *
 * @param {AbstractSDC} controller - js controller instance
 * @param {jquery} $html - jQuery loaded content
 * @return {Promise<*>} - return of the onLoad function
 */
function runControllerShow(controller, $html) {
    return runControllerFillContent(controller, $html).then(function (args) {
        args = args || true;
        if (controller.willShow) {
            let loadPromiseOrContent = controller.willShow();
            if (loadPromiseOrContent instanceof Promise) {
                return loadPromiseOrContent.then(function () {
                    return args;
                });
            }
        }

        return args;
    });
}



/**
 * runControllerLoad Calls the onLoad function of the controller.
 * This function is called before the HTML is set to the page.
 * The parameter is a list of children of the tag and the registered tag.
 *
 * @param {AbstractSDC} controller - js controller instance
 * @return {Promise<*>} - return of the onLoad function
 */
function runControllerLoad(controller) {
    return loadFilesFromController(controller).then((html) => {
        if (!controller.onLoad || controller._onLoadDone) {
            return promiseDummyFactory();
        }

        controller._onLoadDone = true;
        let loadPromise = controller.onLoad(html);
        return (loadPromise || promiseDummyFactory()).then(() => {
            return html;
        });
    });
}

/**
 * runControlFlowFunctions runs the control flow functions:
 * 1. onLoad()
 * 2. fill content
 * 3. willShow(dom parameter)
 * 4. afterShow()
 *
 * @param controller
 */
export function runControlFlowFunctions(controller) {
    return runControllerLoad(controller)
        .then(function ($html) {
            return runControllerShow(controller, $html);
        }).then(() => {
            setupEvents(controller);
            return controller.afterShow && controller.afterShow();
        });
}