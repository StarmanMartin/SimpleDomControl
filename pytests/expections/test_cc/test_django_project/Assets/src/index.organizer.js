import {} from "./test_app_one/test_app_one.organizer.js";
import {} from "./sdc_tools/sdc_tools.organizer.js";
//import {} from "./sdc_user/js/sdc_user.organizer.js";
import {app} from './simpleDomControl/sdc_main.js';

Promise.all([import('jquery'), import('bootstrap')]).then(([{default: $}, bootstrap])=> {
    window['jQuery'] = window['$'] = $;
    app.init_sdc().then(()=> {});
});