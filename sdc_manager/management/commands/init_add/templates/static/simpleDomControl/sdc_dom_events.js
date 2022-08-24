/**
 * switchedDomSelectorAndEvent if string is a CSS class or CSS id selector or an event.
 * Based on this it decides if domSelector is the selector or eventType is the selector.
 * If domSelector is the selector it says true.
 *
 * @param domSelector - selector or event string
 * @param eventType - selector or event string
 * @returns {boolean|*} - If the domSelector is a selector and not the eventType
 */
function switchedDomSelectorAndEvent(domSelector, eventType) {
    return (!/^[.#]/.test(domSelector) && /^[.#]/.test(eventType)) || typeof eventType === 'object' || eventType === 'this' || eventType.startsWith("$.");
}

/**
 * generateEventHandler wraps the event handler and binds this to the the controller.
 *
 * @param controller - a instance of a JavaScript controller object.
 * @param handler - origin handler function
 * @returns {Function} - wrapped handler function
 */
function generateEventHandler(controller, handler) {
    return function (ev) {
        const args = Array.from(arguments);
        args.unshift(this);
        handler.apply(controller, args);
    }
}

/**
 * bindEvent binds all HTML event handlers based on the events-object of
 * the controller for a given container.
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 * @param $content - a jQuery object to bind all controller events.
 * @param events - a jQuery object to bind all controller events.
 */
function bindEvent(controller, $content, events) {
    for (let firstEventKey in events) {
        if (events.hasOwnProperty(firstEventKey)) {
            let eventList = events[firstEventKey];
            for (let secondEventKey in eventList) {
                if (eventList.hasOwnProperty(secondEventKey)) {
                    let handler = eventList[secondEventKey];
                    let domSelector = secondEventKey;
                    let eventType = firstEventKey;
                    if (switchedDomSelectorAndEvent(secondEventKey, firstEventKey)) {
                        domSelector = firstEventKey;
                        eventType = secondEventKey;
                    }

                    let eventCheckClass = `${controller._uuid}_${eventType}`;
                    $content.find(`${domSelector}:not(.${eventCheckClass})`)
                        .on(eventType, generateEventHandler(controller, handler))
                        .addClass(eventCheckClass);
                }
            }
        }
    }
}

/**
 * unbindEvent unbinds all HTML event handlers based on the events-object of
 * the controller for a given container.
 *
 * @param controller - a instance of a JavaScript controller object.
 * @param $content - a jQuery object to unbinds all controller events.
 * @param events - a jQuery object to unbinds all controller events.
 */
function unbindEvent(controller, $content, events) {
    for (let firstEventKey in events) {
        if (events.hasOwnProperty(firstEventKey)) {
            let eventList = events[firstEventKey];
            for (let secondEventKey in eventList) {
                if (eventList.hasOwnProperty(secondEventKey)) {
                    let domSelector = secondEventKey;
                    let eventType = firstEventKey;
                    if (switchedDomSelectorAndEvent(secondEventKey, firstEventKey)) {
                        domSelector = firstEventKey;
                        eventType = secondEventKey;
                    }

                    let eventCheckClass = `${controller._uuid}_${eventType}`;
                    $content.find(domSelector).unbind(eventType).removeClass(eventCheckClass);

                }
            }
        }
    }
}

/**
 * unbindAllControllerEvent unbinds all HTML event handlers based on the events-object of
 * the controller for a given container.
 *
 * @param controller - a instance of a JavaScript controller object.
 * @param $content - a jQuery object to unbind all controller events.
 */
function unbindAllControllerEvent(controller, $content) {
    if (controller.events instanceof Array) {
        for (let i = 0; i < controller.events.length; i++) {
            unbindEvent(controller, $content, controller.events[i]);
        }

        return;
    }

    unbindEvent(controller, $content, controller.events);
}

/**
 * bindAllControllerEvent binds all HTML event handlers based on the events-object of
 * the controller for a given container. This function iterates over the super controller
 * events.
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 * @param {jquery} $content - a jQuery object to bind all controller events.
 */
function bindAllControllerEvent(controller, $content) {
    let events = controller.events;
    if (controller.events instanceof Array) {
        for (let i = 0; i < controller.events.length; i++) {
            bindEvent(controller, $content, controller.events[i]);
        }

        return;
    }

    bindEvent(controller, $content, controller.events);
}

/**
 * setupEvents handlers uses the the events-object of
 * the controller. It binds all all HTML event handler using the events-object
 * of the controller.
 *
 * No action if the controler has no events object.
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 */
export function setupEvents(controller) {
    if (!controller.events) {
        return true;
    }

    let $content = controller.$container;

    bindAllControllerEvent(controller, $content);

}

/**
 * unbindEvents  unbinds all HTML event handlers based on the events-object of
 * the controller.
 *
 * No action if the controler has no events object.
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 */
export function unbindEvents(controller) {
    if (!controller.events) {
        return true;
    }

    let $content = controller.$container;

    unbindAllControllerEvent(controller, $content);
}

/**
 * setupEvents first unbinds all HTML event handlers based on the events-object of
 * the controller. Then it rebinds all all HTML event handler using the events-object
 * of the controller.
 *
 * No action if the controler has no events object.
 *
 * @param {AbstractSDC} controller - a instance of a JavaScript controller object.
 */
export function updateEvents(controller) {
    if (!controller.events) {
        return true;
    }

    let $content = controller.$container;

    bindAllControllerEvent(controller, $content);
}