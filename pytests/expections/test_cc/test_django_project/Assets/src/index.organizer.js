import {} from "./test_app_one/test_app_one.organizer.js";
import {} from "./sdc_tools/sdc_tools.organizer.js";
import {} from "./sdc_user/sdc_user.organizer.js";
import {app} from 'sdc_client';

import('jquery').then(({default: $})=> {
    window['jQuery'] = window['$'] = $;
    Promise.all([import('bootstrap/dist/js/bootstrap.bundle.js'), import('lodash')]).then(([bootstrap, lodash])=> {
        window['Modal'] = bootstrap.Modal;
        window['_'] = lodash.default;
        app.init_sdc().then(()=> {});
    });
});