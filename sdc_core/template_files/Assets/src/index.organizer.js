import {} from "./sdc_tools/sdc_tools.organizer.js";
import {} from "./sdc_user/sdc_user.organizer.js";
import {app} from 'sdc_client';


Promise.all([
    import('jquery'),
    import('bootstrap/dist/js/bootstrap.bundle.js'),
    import('lodash')]).then(([jquery, bootstrap, lodash]) => {
    window['Modal'] = bootstrap.Modal;
    window['jQuery'] = window['$'] = jquery.default;
    window['_'] = lodash.default;
    app.init_sdc()
        .then(() => {
        });
});