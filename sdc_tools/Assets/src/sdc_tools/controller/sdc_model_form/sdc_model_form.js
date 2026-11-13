import { AbstractSDC, app, trigger, SdcQuerySet, SdcModel } from 'sdc_client';
import { modelErrorElement } from '../sdc_error/sdc_error.js';


/**
 * Generic create/edit form for one record of an SDC model, generated from the model's server-side form; saves via the model socket.
 *
 * - Arguments: `model` (required) is the SDC model name; with `pk` (or `id`) it edits that record, without it it creates a new one (e.g. `/~sdc-model-form~&model=Author&pk=3`).
 * - Edit mode: every field change is saved automatically, there is no save step; with `form_name=<name>` a named alternative form of the model is used, and with `auto_save=false` changes are only stored when the save button (`button_text`, default "Save") is pressed.
 * - Create mode: "Create" creates the record and then navigates to `next` (default `..`, one level up); `reset_on_save=true` instead clears the form for another entry, `editing_after_save=true` switches to editing the new record.
 * - After a successful save of an existing record the form navigates to `next` if given.
 * - Other optional arguments: `form_header` (heading text) and `filter` (selects the record to edit instead of `pk`).
 * - Validation errors are shown at the fields; who may create or edit is decided by the model's server-side permissions.
 * - Also used as a mixin by app-specific form controllers.
 */
export class SdcModelFormController extends AbstractSDC {


  constructor() {
    super();
    this.id = null;
    this.contentUrl = "/sdc_view/sdc_tools/sdc_model_form"; //<sdc-model-form></sdc-model-form>
    this.model_name = null;
    this.isKeepEditing = null;
    this.isReset = null;
    this._isLoaded = false;
    this._loadError = null;
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
  // - onLoad (DOM not set)                          //
  // - willShow  (DOM set)                           //
  // - onRefresh  (recalled on reload)              //
  //-------------------------------------------------//
  // - onRemove                                      //
  //-------------------------------------------------//
  async onInitForm({
                     model,
                     pk,
                     id,
                     next,
                     filter = null,
                     on_update,
                     on_error,
                     form_header,
                     button_text,
                     form_name = false,
                     reset_on_save = false,
                     editing_after_save = false,
                     auto_save = true
                   }) {

    this.on_update ??= on_update;
    this.on_error ??= on_error;
    this.next ??= next;
    this.buttonText ??= button_text || gettext('Save');
    this.formHeader ??= form_header;
    this.autoSave ??= auto_save;
    this.isReset ??= reset_on_save;
    this.isKeepEditing ??= editing_after_save;
    this.id ??= id ?? pk;
    this.form_name ??= form_name;


    if (this.id) {
      filter = { id: this.id  };
    } else if (typeof filter === 'function') {
      filter = filter();
    }

    if (this.model) {
      model = this.model;
    }

    if (model instanceof Promise) {
      model = await model;
    }

    if (typeof model === 'object' && model instanceof SdcModel) {
      this.model = model;
      this.id ??= model.id;
    } else if (typeof model !== 'object') {
      this.model = this.querySet(this.model_name || model, filter);
    } else if (typeof model === 'object' && model instanceof SdcQuerySet) {
      this.model = model;
    }

    if (typeof this.model === 'object' && this.model instanceof SdcQuerySet) {
      if(Object.keys(this.model.modelQuery).length === 0) {
        this.id = null;
        this.model = this.model.new();
      } else {
        try {
          this.model = await this.model.get();
          this.id = this.model.id;
        } catch (e) {
          if (e?.is_error) {
            // The server refused the model (SdcModelError, e.g. 403): no create form as a fallback.
            throw e;
          }
          this.id = null;
          this.model = this.model.new();
        }
      }
    }
    if (typeof (this.id) === "undefined" || this.id === null) {
      this.isAutoChange = false;
      this.type = 'create';
      this.formGenerator = (modelObj) => modelObj.form({
        cbResolve: this._onFormLoaded.bind(this),
        cbReject: this._onFormError.bind(this)
      });
    } else if (this.form_name) {
      this.isAutoChange = this.autoSave;
      this.type = 'edit';
      this.formGenerator = (modelObj) => modelObj.namedForm({
        formName: this.form_name,
        cbResolve: this._onFormLoaded.bind(this),
        cbReject: this._onFormError.bind(this)
      });
    } else {
      this.isAutoChange = true;
      this.type = 'edit';
      this.formGenerator = (modelObj) => modelObj.form({
        cbResolve: this._onFormLoaded.bind(this),
        cbReject: this._onFormError.bind(this)
      });
    }

  }

  async onLoad($html) {
    await this.onInitForm(this.params).catch((e) => {
      this.model = null;
      this._loadError = e;
      if (!e?.is_error) {
        // An SdcModelError (e.g. 403) was already reported to the user by the model socket.
        console.error(e);
      }
    });
    if (this.model) {
      this.form = this.formGenerator(this.model).addClass('container-fluid');
      $html.find('.form-container').append(this.form);
    } else {
      $html.find('.form-container').append(modelErrorElement(this._loadError));
      $html.find('.btn-container').remove();
      this._isLoaded = true;
    }
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

  _onFormError(err) {
    // The server refused the form (e.g. 403): show the error instead of "Loading..." and the form buttons.
    this._loadError = err;
    this._isLoaded = true;
    this.find('.form-container').safeEmpty().append(modelErrorElement(err));
    this.find('.btn-container').remove();
    this.refresh();
  }

  _createFormToEditForm() {
    this.id = this.model.id;
    this.type = 'edit';
    this.isAutoChange = true;
    const oldForm = this.form?.closest('form');
    const newForm = oldForm.clone();
    const fc = newForm.find('.form-container').safeEmpty();
    const newFormContent = this.model.form({
      cbResolve: () => {
        this.reconcile(newForm, oldForm);
      }
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
          self.model.querySet.setIds(self.model.id);
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
    if (!this.model || !this.type) {
      return super.controller_name();
    }
    return `${this.type.replace(/^./g, letter => letter.toUpperCase())} ${this.model.constructor.name.replace(/[A-Z]/g, letter => " " + letter).replace(/^./g, letter => letter.toUpperCase())}`
  }

  save_btn() {
    if (this._loadError) {
      return <span></span>;
    }
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