import {AbstractSDC, app, trigger} from 'sdc_client';


export class SdcModelFormController extends AbstractSDC {


  constructor() {
    super();
    this.pk = null;
    this.contentUrl = "/sdc_view/sdc_tools/sdc_model_form"; //<sdc-model-form></sdc-model-form>
    this.model_name = null;
    this.isKeepEditing = null;
    this.isReset = null;
    this._isLoaded = false;
    this.autoSave = null;
    this.model = null;
    this.formHeader = null;
    this.buttonText = null;

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
  onInit(model, pk, next, filter = null, on_update, on_error, form_header, button_text, form_name = false, reset_on_save = false, editing_after_save = false, auto_save = true) {
    !this.on_update && (this.on_update = on_update);
    !this.on_error && (this.on_error = on_error);
    !this.next && (this.next = next);

    if (this.buttonText === null && button_text) {
      this.buttonText = button_text;
    } else {
      this.buttonText = gettext('Save');
    }

    if (this.formHeader === null) {
      this.formHeader = form_header;
    }
    if (this.autoSave === null) {
      this.autoSave = auto_save;
    }
    if (this.isReset === null) {
      this.isReset = reset_on_save;
    }
    if (this.isKeepEditing === null) {
      this.isKeepEditing = editing_after_save;
    }

    if (typeof filter === 'function') {
      filter = filter();
    }

    if (typeof model === 'object' && model.constructor.name === 'Model') {
      this.model = model;
    } else if (model instanceof Promise) {
      this.model = model;
    }else if (model) {
      this.model = null;
    }

    if (this.model && this.model?.pk > 0) {
      pk = this.model.pk;
    } else if (!model && this.model_name) {
      model = this.model_name;
    }

    const querySet = this.querySet(model, filter);
    this.form_name ||= form_name;

    if (this.form_name) {
      this.isAutoChange = this.autoSave;
      this.pk = pk;
      this.type = 'edit';
      this.model ??= querySet.setIds(pk)[0];
      this.formGenerator = (modelObj) => modelObj.namedForm({
        formName: this.form_name,
        cbResolve: this._onFormLoaded.bind(this)
      });
    } else if (typeof (pk) !== "undefined") {
      this.isAutoChange = true;
      this.pk = pk;
      this.type = 'edit';
      this.model ??= querySet.setIds(pk)[0];
      this.formGenerator = (modelObj) => modelObj.form({cbResolve: this._onFormLoaded.bind(this)});
    } else {
      this.isAutoChange = false;
      this.type = 'create';
      this.model ??= querySet.new();
      this.formGenerator = (modelObj) => modelObj.form({cbResolve: this._onFormLoaded.bind(this)});
    }

  }

  async onLoad($html) {
    if (this.model instanceof Promise) {
      this.model = await this.model;
    }
    this.form = this.formGenerator(this.model).addClass('container-fluid');
    $html.find('.form-container').append(this.form);
    // $html.find(`.not-${this.type}`).remove();
    return super.onLoad($html);
  }

  onChange() {
    this.form?.closest('form').submit();
  }

  willShow() {
    return super.willShow();
  }

  onRefresh() {
    return super.onRefresh();
  }

  _onFormLoaded() {
    if (!this._isLoaded) {
      this.refresh();
    }
    this._isLoaded = true;
  }

  _createFormToEditForm() {
    this.pk = this.model.values.pk;
    this.type = 'edit';
    this.isAutoChange = true;
    const oldForm = this.form?.closest('form');
    const newForm = oldForm.clone();
    const fc = newForm.find('.form-container').safeEmpty();
    const newFormContent = this.model.editForm(this.pk, () => {
      this.reconcile(newForm, oldForm);
    }).addClass('container-fluid');
    fc.append(newFormContent);
  }

  submitModelForm($form, e) {
    let self = this;
    return super.defaultSubmitModelForm($form, e).then(function (res) {
      let runNext = true;
      if (res && res.type === 'create') {
        runNext = false;
        if (self.isReset) {
          $form[0].reset();
        } else if (self.isKeepEditing) {
          self._createFormToEditForm();
        } else {
          trigger('goTo', self.next || '..');
        }
      }

      self.on_update && self.on_update(res);

      if (runNext && self.next) {
        trigger('goTo', self.next);
      }
    }).catch((res) => {
      self.on_error && self.on_error(res);
    });
  }

  controller_name() {
    return `${this.type.replace(/^./g, letter => letter.toUpperCase())} ${this.model.constructor.name.replace(/[A-Z]/g, letter => " " + letter).replace(/^./g, letter => letter.toUpperCase())}`
  }

  save_btn() {
    if (!this._isLoaded) {
      return <h3>{gettext('Loading...')}</h3>;
    }
    if (!this.autoSave && this.type === 'edit') {
      return <button className="btn btn-success">{this.buttonText}</button>;

    }
    return <span></span>;
  }

  header_top() {
    if (this.formHeader) {
      return <h3>{this.formHeader}</h3>;

    }
    return <span></span>;
  }

}

app.register(SdcModelFormController).addMixin('sdc-update-on-change');