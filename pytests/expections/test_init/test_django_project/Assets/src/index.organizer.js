import {} from "./sdc_tools/sdc_tools.organizer.js";
import {} from "./sdc_user/sdc_user.organizer.js";
import {app} from './simpleDomControl/sdc_main.js';

import('jquery').then(({default: $})=> {
    window['jQuery'] = window['$'] = $;
    Promise.all([import('bootstrap/dist/js/bootstrap.bundle')]).then(()=> {
        app.init_sdc().then(()=> {});
    });
});