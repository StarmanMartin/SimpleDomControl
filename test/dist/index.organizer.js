import "./sdc_tools/sdc_tools.organizer.js";
import "./sdc_user/sdc_user.organizer.js";
import { app } from './simpleDomControl/sdc_main.js';
import('jquery').then(({
  default: $
}) => {
  window['jQuery'] = window['$'] = $;
  Promise.all([import('bootstrap/dist/js/bootstrap.bundle')]).then(res => {
    window['Modal'] = res[0].Modal;
    app.init_sdc().then(() => {});
  });
});