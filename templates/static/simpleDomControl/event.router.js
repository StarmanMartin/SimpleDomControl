(function (app) {
    /**
     * The public events objects
     * @type {{}}
     */
    app.events = {};

    /**
     * A list of handler (controller) for the registered events.
     * @type {{}}
     */
    var handlerList = {};

    /**
     * eventList is a map connection the event to a responsing function name.
     * @type {{}}
     */
    var eventList = {};

    /**
     * on is a function to register a controller to a event. The controller has to
     * implement the the handler function. The handler functions by default has the same
     * name as the event. You can use the app.events.setEvent function to register a
     * event with a different named function.
     *
     * @param name - the event name String
     * @param controller -  a instance of a JavaScript controller object.
     */
    app.events.on = function (name, controller) {
        app.events.setEvent(name);
        if (!eventList.hasOwnProperty(name)) {
            return console.log('No event: ' + name, controller);
        }

        var funcName = eventList[name];
        if (!controller[funcName]) {
            return console.log('No event handler: ' + name, controller);
        }

        handlerList[name].push(controller);
    };

    /**
     * setEvent allows you to register a event with a function with a different
     * name as the event.
     *
     * @param name - event name
     * @param functionName - function name
     */
    app.events.setEvent = function (name, functionName) {
        if (!functionName) {
            functionName = name;
        }

        if (!eventList[name]) {
            eventList[name] = functionName;
            handlerList[name] = [];
        }
    };

    /**
     * allOff is to remove all events of the controller instance
     * ! important before destroying the instance.
     *
     * @param controller - a instance of a JavaScript controller object.
     */
    app.events.allOff = function (controller) {
        for (var eventName in handlerList) {
            if (handlerList.hasOwnProperty(eventName)) {
                for (var i = handlerList[eventName].length; i >= 0; i--) {
                    if (controller === handlerList[eventName][i]) {
                        handlerList[eventName].splice(i, 1);
                    }
                }
            }
        }
    };

    /**
     * trigger triggers the event. The handler function of all registered
     * controller gets called. The returned Promise returns a list with all
     * returned values.
     *
     * @param name - event name
     * @returns {Promise<object>} - waits to return all return values of the handler
     */
    app.events.trigger = function (name) {
        var args = Array.apply(null, arguments);
        name = args.shift();
        var handler = handlerList[name];
        var funcName = eventList[name];

        var list = [];

        for (var i = 0; i < handler.length; i++) {
            var return_val = handler[i][funcName].apply(handler[i], args);
            if (typeof return_val !== "undefined") {
                list.push(return_val);
            }
        }

        return Promise.all(list)
    }


})(window.app || (window.app = {}));