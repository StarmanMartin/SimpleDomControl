(function (app) {
    app.simpleDomInit = function (app) {

        var controllers = [
            //## controller-src-section-start ##//
            //## controller-src-section-end ##//
        ];

        app.setContentUrlPrefix('');
        app.setMainContainer($('.super-container'));
        app.registerControllerList(controllers, IS_DEBUG);
    };
})(window.app || (window.app = {}));