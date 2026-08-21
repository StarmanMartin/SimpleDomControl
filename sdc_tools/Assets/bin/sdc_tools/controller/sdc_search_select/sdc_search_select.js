import { AbstractSDC, app } from 'sdc_client';


class SdcSearchSelectController extends AbstractSDC {

  constructor() {
    super();
    this.contentUrl = "/sdc_view/sdc_tools/sdc_search_select"; //<sdc-search-select></sdc-search-select>
    this._state = 0;
    this._searchIdx = {};
    this._searchtimer = null;
    this._currentOption = [];
    this.startValues = [];
    this.value = [];
    this._allowDelete = false;
    this.model = null;
    /**
     * Uncomment the following line to make sure the HTML template
     * of this controller is not cached and reloaded for every instance
     * of this controller.
     */
    // this.contentReload = true;

    /**
     * Uncomment the following line to make this controller asynchronous.
     * This means that the parent controller finishes loading without
     * waiting for this controller
     */
    // this.load_async = true;

    /**
     * Events is an array of dom events.
     * The pattern is {'event': {'dom_selector': handler}}
     * Uncomment the following line to add events;
     */
    this.events.unshift({
      'click': {
        '.option-container': function ($btn) {
          this.onSelect($btn);
        }
      }
    });
  }

  //-------------------------------------------------//
  // Lifecycle handler                               //
  // - onLoad (DOM not set)                          //
  // - willShow  (DOM set)                           //
  // - onRefresh  (recalled on reload)              //
  //-------------------------------------------------//
  // - onRemove                                      //
  //-------------------------------------------------//

  onInitSearchSelect({ name = 'unknown', required, value = [''], modelName, multiple, ids }) {
    this.required = Boolean(required?.toLocaleLowerCase() === 'true');
    this.multi = Boolean(multiple?.toLocaleLowerCase() === 'true');
    this._allowDelete = !this.required || this.multi;
    if (value instanceof Array) {
      this.startValues = value;
    } else {
      this.startValues = JSON.parse(value.replaceAll("'", '"'));
    }
    this.name = name;
    if (modelName) {
      if (ids) {
        this.model = this.newModel(modelName, { pk__in: ids });
      } else {
        this.model = this.newModel(modelName);
      }

    }
  }

  onLoad($html) {
    this.onInitSearchSelect(this.params);
    if (!this.model) {
      let self = this;
      const $allOptions = $('<div class="all-option-container"></div>');
      $html.find('.main-select-options').append($allOptions);
      this.find('.option-container').each(function () {
        self._prepareOption(this);
        $allOptions.append(this);
      });
    }
    return super.onLoad($html);

  }

  willShow() {
    if (!this.model) {
      return super.willShow();
    }
    return new Promise((resolve) => {
      const self = this;
      const $div = this.model.view({
        viewName: 'html_select_template',
        cbResolve: () => {
          self.find('.option-container').each(function () {
            self._prepareOption(this);
          });
          resolve(super.willShow());
        }
      });
      $div.removeClass('container-fluid').addClass('all-option-container');
      this.find('.main-select-options').append($div);
    });

  }

  _prepareOption(option) {
    const $option = $(option);
    const idx = String($option.data('value'));
    const safeIdx = idx.replace(/[^a-zA-Z0-9_-]+/g, "__");
    this._searchIdx[safeIdx] = $option.data('search').toLowerCase().split(',').map((x) => x.replaceAll(' ', ''));
    this._searchIdx[safeIdx].push($option.data('search'));
    $option.addClass(`oc-${safeIdx}`).addClass('oc-style');
    if (this.startValues.includes(idx)) {
      this._storeSelectedOption($option);
    }
  }

  onRefresh() {
    if (this._state === 1) {
      setTimeout(() => this.find('.search-term-input').focus(), 100);
      this.find('.main-select-options').addClass('active').find('.search-term-input').val('');
      this.find('.option-container').addClass('found');
    } else {
      this.find('.main-select-options').removeClass('active');
    }
    return super.onRefresh();
  }

  current_val() {
    if (this._state === 0) {
      if (this.value.length === 0) {
        return <div>
          <p sdc_click="onActivate" className="mb-2 custom-select form-control">
            <span className="select-label">{gettext('Search & select...')}</span>
            <span className="select-arrow"></span>
          </p>
          <input type="hidden" className="timer-change" name={this.name} value=""/>
        </div>
      }

      let values;
      if (this.multi) {
        values = `[${this.value.join(',')}]`;
      } else {
        values = this.value[0];
      }
      return <div sdc_click="onActivate" className={this.multi ? 'multi custom-select-selected' : 'custom-select-selected'}>
        {this._currentOption.map(this._optionBtnToSelected.bind(this))}
        <input className="timer-change" type="hidden" name={this.name} value={values}/>
            <span className="select-arrow"></span>
      </div>
    }
  }

  onActivate() {
    this._state = 1;
    this.refresh();

  }

  onDeactivate($btn, e) {
    const elementUnderMouse = document.elementFromPoint(e.clientX, e.clientY);
    if ($(elementUnderMouse).hasClass('background-event')) {
      this._deactivate();
    }
  }

  _deactivate() {
    return new Promise((resolve) => {
      setTimeout(() => {
        this._state = 0;
        resolve(this.refresh());
      }, 100);
    });
  }

  _optionBtnToSelected($btn) {
    const currentOption = $btn.clone()[0];
    // copy attributes into array first (NamedNodeMap is live)
    Array.from(currentOption.attributes).forEach(attr => currentOption.removeAttribute(attr.name));
    currentOption.className = "selected-option";
    const newVal = String($btn.data('value'));

    if (this._allowDelete) {
      const delBtn = $('<button type="button" sdc_click="remove_selection" class="delete-btn" aria-label="Remove Bouldering">&times;</button>');
      delBtn.data('value', newVal)
      currentOption.append(delBtn[0]);
    }

    return currentOption;
  }

  _storeSelectedOption($btn) {
    const newVal = String($btn.data('value'));
    $btn.addClass('selected');
    if (!this.multi) {
      this.value = [newVal];
      this._currentOption.forEach(($selBtn) => $selBtn.removeClass('selected'));
      this._currentOption = [$btn];
    } else if (!this.value.includes(newVal)) {
      this.value.push(newVal);
      this._currentOption.push($btn);
    }
  }

  remove_selection($btn, e) {
    e.stopPropagation();
    const idx = this.value.indexOf($btn.data('value'));
    this.value.splice(idx, 1);
    const [$selBtn] = this._currentOption.splice(idx, 1);
    $selBtn.removeClass('selected');
    this.refresh().then(() => {
      this.find('.timer-change').trigger('change');
    });
  }

  onSelect($btn) {
    this._storeSelectedOption($btn);
    this._deactivate().then(() => {
      this.find('.timer-change').trigger('change');
    });
    ;
  }

  updateSearch($btn) {
    if (this._searchtimer) {
      clearTimeout(this._searchtimer);
    }

    this._searchtimer = setTimeout(() => {
      this.find('.option-container').removeClass('found');
      const searchVals = $btn.val().toLowerCase().split(/[,\s]+/);
      if (!searchVals) {
        return;
      }
      Object.entries(this._searchIdx).forEach(([value, searchTerms]) => {
        if (searchVals.every((toFind) => searchTerms.some((term) => term.includes(toFind)))) {
          this.find(`.oc-${value}`).addClass('found');
        }
      });

    }, 500);
  }

}

app.register(SdcSearchSelectController);