import {} from "./sdc_tools/sdc_tools.organizer.js";
import {} from "./sdc_user/sdc_user.organizer.js";
import {app} from 'sdc_client';

import('jquery').then(({default: $})=> {
    window['jQuery'] = window['$'] = $;
    Promise.all([import('bootstrap/dist/js/bootstrap.bundle.js')]).then((res)=> {
        window['Modal'] = res[0].Modal;
        app.init_sdc().then(()=> {});
    });
});