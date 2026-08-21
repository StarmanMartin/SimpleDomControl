import { AbstractSDC, app, SdcModel, SdcQuerySet } from 'sdc_client';


export class SdcDetailViewController extends AbstractSDC {

  constructor() {
    super();
    this.contentUrl = "/sdc_view/sdc_tools/sdc_detail_view"; //<sdc-detail-view></sdc-detail-view>
    this.template_context = null;
    this.model = null;

    /**
     * Events is an array of dom events.
     * The pattern is {'event': {'dom_selector': handler}}
     * Uncommend the following line to add events;
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

  async onInitDetails({ model, pk, id }) {
    this.id ??= id ?? pk;

    if (this.model) {
      model = this.model;
    }

    if (model instanceof Promise) {
      model = await model;
    }

    if (typeof model === 'object' && model instanceof SdcModel) {
      this.model = model;
      this.querySetInstance = model.querySet;
      return;
    }

    if (typeof model === 'object' && model instanceof SdcQuerySet) {
      this.querySetInstance = model;
    }

    if (typeof model !== 'object') {
      this.querySetInstance = this.querySet(this.model_name || model, { id: this.id  });
    }

    this.model = await this.querySetInstance.get();
  }

  async onLoad($html) {
    await this.onInitDetails(this.params);

    const $dt = this.model.detailView({
      cbResolve: () => {
        let $lc = this.find('.detail-container');
        $lc.append($dt);
        this.refresh().then(r => null);
        this._onUpdate.bind(this);

      }, templateContext: this.template_context
    });
    if (this.querySetInstance) {
      this.querySetInstance.onUpdate = async () => {
        await this._updateView();
        this._onUpdate();
      };
    }
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

  _onUpdate() {
    if (this.on_update) {
      this.model.update().then(() => {
        this.on_update(this.model);
      });
    }
  }

  _updateView() {
    return new Promise((resolve) => {
      const $div = this.model.detailView({
        cbResolve: () => {
          const elems = $('.tooltip.fade.show');
          elems.remove();
          app.reconcile(this, $div, this.find('.detail-container').children());
          resolve();
        }, templateContext: this.template_context
      });
    });

  }

}

app.register(SdcDetailViewController);