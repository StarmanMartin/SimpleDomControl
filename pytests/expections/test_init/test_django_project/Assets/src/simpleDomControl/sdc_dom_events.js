import {CONTROLLER_CLASS, getController} from './sdc_view.js';

export const STD_EVENT_LIST = Object.keys(window).filter(key => /^on/.test(key)).map(x => x.slice(2));


export function windowEventHandler(event) {
    let ev_type = event.type;
    if (event.hasOwnProperty('namespace')) ev_type += `.${event.namespace}`;
    let $elm = $(event.target);
    let controller = null;
    let is_done = false;
    let is_last_elem = false;
    event.stopImmediatePropagation = () => is_last_elem = true;
    event.stopPropagation = () => is_last_elem = is_done = true;
    while ($elm.length) {
        let attrs = $elm.attr(`sdc_${ev_type}`);
        if (attrs) {
            if (!controller) {
                controller = getController($elm);
                if (!controller) return;
            }
            while (controller) {
                attrs.split(' ').forEach((attr) => {
                    if (is_done) return;
                    let handler = null;
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
                controller = controller._parentController
            }
        }
        if (is_done) return;
        $elm = $elm.parent();
    }

    return {res: true};
}

/**
 *
 */
export function initEvents() {
    const $window = $(window);
    STD_EVENT_LIST.forEach(ev_type => {
        $window.on(ev_type, windowEventHandler);
    });
}


/**
 *
 * @param {AbstractSDC} controller
 */
export function setControllerEvents(controller) {

    if (controller.isEventsSet) {
        return;
    }

    const events = controller.getEvents();
    for (let ev_type in events) {
        if (events.hasOwnProperty(ev_type)) {
            let eventList = events[ev_type];
            for (let domSelector in eventList) {
                if (eventList.hasOwnProperty(domSelector)) {
                    controller.find(domSelector).each(function () {
                        let $elements = $(this);
                        let event_list = $elements.attr(`sdc_${ev_type}`) || null;
                        if (!event_list) event_list = [];
                        else event_list = event_list.split(' ');
                        const new_key = `this.event_${domSelector}`;
                        if (event_list.indexOf(new_key) === -1) {
                            event_list.push(new_key);
                            $elements.attr(`sdc_${ev_type}`, event_list.join(' '))
                        }

                    });
                }
            }
        }
    }

    //controller.isEventsSet = true;
}