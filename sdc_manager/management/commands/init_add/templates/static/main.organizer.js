(function (app) {
    "use strict";

    app.simpleDomInit = function (app) {

        var controllers = [
            //## controller-src-section-start ##//
            //## controller-src-section-end ##//
        ];

        app.setContentUrlPrefix('');
        app.setVersion('0.1');
        app.setMainContainer($('.super-container'));
        app.registerControllerList(controllers, IS_DEBUG);
    };
})(window.app || (window.app = {}));
