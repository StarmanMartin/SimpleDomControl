import {app} from 'sdc_client';

window['sdc_client'] = sdc_client;

await (async () => Promise.all([
  // SDC APP import
  import("#lib/sdc_user/sdc_user.organizer.js"),
  import("#lib/sdc_tools/sdc_tools.organizer.js"),
]))();


Promise.all([
  import('jquery'),
  import('bootstrap/dist/js/bootstrap.bundle.js'),
  import('lodash')]).then(([jquery, bootstrap, lodash]) => {
  window['Modal'] = bootstrap.Modal;
  window['Tooltip'] = bootstrap.Tooltip;
  window['jQuery'] = window['$'] = jquery.default;
  window['_'] = lodash.default;
  app.init_sdc()
    .then(() => {
    });
});