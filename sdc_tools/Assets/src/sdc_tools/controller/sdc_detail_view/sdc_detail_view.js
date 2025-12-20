import {AbstractSDC, app} from 'sdc_client';


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
  // - onInit (tag parameter)                        //
  // - onLoad (DOM not set)                          //
  // - willShow  (DOM set)                           //
  // - onRefresh  (recalled on reload)              //
  //-------------------------------------------------//
  // - onRemove                                      //
  //-------------------------------------------------//

  onInit(model, pk) {
    if (!this.model) {
      if (!model || typeof pk === 'undefined') {
        console.error("You have to set data-model and data-pk in the <sdc-detail-view> tag!");
      }

      this.model = this.newModel(model, {pk: pk});
    }
  }

  onLoad($html) {
    const $dt = this.model.detailView(null, () => {
      let $lc = this.find('.detail-container');
      $lc.append($dt);
      this.refresh();
      this._onUpdate.bind(this);

    }, null, this.template_context);
    this.model.on_update = this.model.on_create = async () => {
      await this._updateView();
      this._onUpdate();
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


  removeInstance($btn, e) {
    this.model.delete();
  }

  _onUpdate() {
    if (this.on_update) {
      this.model.load().then(() => {
        this.on_update(this.model.values_list);
      });
    }
  }

  _updateView() {
    return new Promise((resolve) => {
      const $div = this.model.listView(this.search_values, () => {
        const elems = $('.tooltip.fade.show');
        elems.remove();
        app.reconcile(this, $div, this.find('.detail-container').children());
        resolve();
      }, null, this.template_context);
    });

  }

}

app.register(SdcDetailViewController);