import { AbstractSDC, app, SdcModel, SdcQuerySet } from 'sdc_client';

/**
 * Generic live list of the records of one SDC model, rendered with the model's list template.
 *
 * - Arguments: `model` (required) is the SDC model name, e.g. `/~sdc-list-view~&model=Author`; optional `filter` restricts the records (normally only set from code by a parent view).
 * - The list updates automatically when records are created, changed or deleted (model socket).
 * - An embedded `<sdc-search-view>` (if the model's list template has one) filters and pages the list.
 * - In the default list template each row has "Edit" (opens `<sdc-model-form>`), "Detail" (opens `<sdc-detail-view>`) and "Remove"; "Remove" asks for confirmation in a dialog and then deletes the record on the server; this cannot be undone.
 * - What is listed and whether delete is allowed is decided by the model's server-side permissions.
 */
export class SdcListViewController extends AbstractSDC {

  constructor() {
    super();
    this.contentUrl = "/sdc_view/sdc_tools/sdc_list_view"; //<sdc-list-view></sdc-list-view>
    this.search_values = {};
    this.model_name = null;
    this.template_context = null;

    /**
     * Events is an array of dom events.
     * The pattern is {'event': {'dom_selector': handler}}
     * Uncomment the following line to add events;
     */
    // this.events.unshift({'click': {'.header-sample': (ev, $elem)=> $elem.css('border', '2px solid black')}}});
  }

  //-------------------------------------------------//
  // Lifecycle handler                               //
  // - onLoad (DOM not set)                          //
  // - willShow  (DOM set)                           //
  // - onRefresh  (recalled on reload)              //
  //-------------------------------------------------//
  // - onRemove                                      //
  //-------------------------------------------------//

  async onInitList({ model, filter, onUpdate }) {
    if (this.model) {
      model = this.model;
    }

    if (model instanceof Promise) {
      model = await model;
    }
    this.filter ??= filter;
    this.model_name ??= model;
    this.on_update ??= onUpdate;
    if (typeof this.filter === 'function') {
      this.filter = this.filter();
    }

    if (typeof model === 'object' && model instanceof SdcQuerySet) {
      this.model = model;
    }

    if (typeof model !== 'object') {
      this.model = this.querySet(this.model_name);
    }

    if(this.filter) {
      this.model.setFilter(this.filter);
    }

    if (this.on_update) {
      this.model.load().then(() => {
        this.on_update(this.model);
      });
    }
  }

  onLoad($html) {
    this.onInitList(this.params);
    let lc = $html.filter('.list-container');
    if (lc.length === 0) {
      lc = $html.find('.list-container');
    }

    lc.append(this.model.listView({modelQuery: this.search_values, templateContext: this.template_context}));
    this.model.onUpdate = this.model.onCreate = () => {
      if (this.on_update) {
        this.model.update().then(() => {
          this.on_update(this.model);
        });
      }

      this._updateView();
    };
    return super.onLoad($html);
  }

  willShow() {
    return super.willShow();
  }

  onRefresh() {
    this.find('[data-bs-toggle="tooltip"]').each(function () {
      new Tooltip(this);
    });
    return super.onRefresh();
  }

  removeInstance($btn) {
    this.model.delete({id: $btn.data('instance-pk')});
  }

  onSearch(form) {
    const formData = new FormData(form);
    formData.forEach((value, key) => this.search_values[key] = value);
    this._updateView();
  }

  _updateView() {

    const $div = this.model.listView({
      searchValues: this.search_values,
      templateContext: this.template_context,
      cbResolve: () => {
      const elems = $('.tooltip.fade.show');
      elems.remove();
      app.reconcile(this, $div, this.find('.list-container .container-fluid').first()).then(r => null);
    }
    });
  }
}

app.register(SdcListViewController);