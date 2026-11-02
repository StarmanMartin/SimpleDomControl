import {AbstractSDC, app, SdcQuerySet, trigger} from 'sdc_client';

// Records returned to the model by one model_load action
const MAX_LOADED_RECORDS = 50;
// How long a navigate action waits for the new view
const NAVIGATION_TIMEOUT_MS = 10000;
// read_page: size limits of what is sent to the model
const MAX_PAGE_HTML = 30000;
const MAX_FIELD_VALUE = 500;
const MAX_FIELD_OPTIONS = 50;
// read_page: attributes kept in the simplified HTML (all others are removed)
const PAGE_ATTRIBUTES = ['id', 'name', 'type', 'href', 'value', 'placeholder', 'for', 'role', 'aria-label', 'title',
    'sdc_click', 'sdcmodelname', 'sdcmodelpk', 'checked', 'selected', 'disabled', 'required', 'multiple'];
// Elements of the page the model never sees
const PAGE_SKIPPED = 'script, style, noscript, template, iframe, svg, canvas, sdc-ai-assistant';
// Field types the assistant must not read or fill
const SECRET_TYPES = ['password', 'hidden', 'file'];
// "Remember on this device": settings without the key in localStorage, the key only in sessionStorage
const SETTINGS_STORAGE_KEY = 'sdc_ai_settings';
const TOKEN_STORAGE_KEY = 'sdc_ai_token';
const SETTING_FIELDS = ['provider', 'base_url', 'model', 'effort', 'max_tokens'];
// Position and size of the moved/resized window, kept in localStorage
const WINDOW_STORAGE_KEY = 'sdc_ai_window';
const MIN_WINDOW_WIDTH = 280;
const MIN_WINDOW_HEIGHT = 240;


/**
 * Chat panel of the AI assistant, fixed at the right edge of the page; only rendered when the project sets `SDC_AI_ASSISTANT`.
 *
 * - The user types a question; the answer streams in. The assistant can also act on the page, always with the
 *   logged-in user's permissions: open views like a navigation link, read the current page and enter values into
 *   its forms, and read SdcModel records.
 * - The assistant cannot create, change or delete records and never submits a form: it fills forms (SdcModel forms
 *   are marked by `SdcModelName` / `SdcModelPK`) and the user checks and submits or saves them. It never reads or
 *   fills password, hidden or file fields.
 * - Depending on the project settings it requires a login, and either uses the server's API key or the user's own.
 * - "⚙" opens the settings: with the server's key they only show the model in use; otherwise the user enters their
 *   API key and may choose the provider (Anthropic or any OpenAI-compatible API such as the KIT KI-Toolbox) and set
 *   the API URL (https, public hosts only), model, effort and max tokens. Changing the provider starts a new
 *   conversation. "Remember on this device" keeps the settings in the browser, the key only until the tab is closed.
 * - The panel starts collapsed at the right edge of the page; a click on it (or "⇆") expands it, "⇆" collapses it
 *   again. It opens by itself when the settings need the user's API key.
 * - Dragging the header moves the panel and dragging its edges or corners resizes it (kept in the browser);
 *   a double-click on the header docks it at the right edge again.
 */
class SdcAiAssistantController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/sdc_ai_assistant"; //<sdc-ai-assistant></sdc-ai-assistant>
        this._socket = null;
        this._requestId = 0;
        // Answer bubble the streamed text of the current request goes into
        this._$answer = null;
        // Connection settings reported by the server (ai_config)
        this._config = null;
        // Remembered settings are sent once per connection
        this._restored = false;
        // A set_config of the settings menu waits for the server's answer
        this._savingSettings = false;
        // {left, top, width, height} once the user moved or resized the window; null = docked at the right edge
        this._geometry = null;
        this._onWindowResize = () => this._applyGeometry();

        // Actions the assistant may run (tool names of SDCAiConsumer, see sdc_core/consumers.py)
        // SdcModels are read-only: there are no actions to create, change or delete records
        this._actions = {
            navigate: (input) => this._navigate(input),
            read_page: () => this._readPage(),
            fill_form: (input) => this._fillForm(input),
            model_get: (input) => this._modelGet(input),
            model_load: (input) => this._modelLoad(input),
        };
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - onRefresh  (recalled on reload)              //
    //-------------------------------------------------//
    // - onRemove                                      //
    //-------------------------------------------------//

    onLoad($html) {
        return super.onLoad($html);
    }

    willShow() {
        this.events.unshift({
            'submit': {
                '.ai-prompt-form': ($form, ev) => {
                    ev.preventDefault();
                    this._sendPrompt();
                },
                '.ai-settings-form': ($form, ev) => {
                    ev.preventDefault();
                    this._saveSettings();
                },
            },
            'click': {
                '.ai-toggle': (_$elm, e) => {
                    e.stopPropagation();
                    this._setCollapsed(!this.find('.ai-conversation-container').hasClass('collapsed'));
                },
                '.ai-conversation-container': ($elm) => $elm.hasClass('collapsed') && this._setCollapsed(false),
                '.ai-settings-toggle': () => this._showSettings(this.find('.ai-settings-form').hasClass('d-none')),
                '.ai-settings-cancel': () => this._showSettings(false),
            },
            'keydown': {
                // Enter sends, Shift+Enter adds a line break
                '.ai-prompt-form textarea': ($textarea, ev) => {
                    if (ev.key === 'Enter' && !ev.shiftKey) {
                        ev.preventDefault();
                        this._sendPrompt();
                    }
                },
            },
        });
        // The template is empty when the assistant is disabled on the server
        if (this.find('.ai-conversation-container').length) {
            this._setUpWindow();
            this._connect();
        }
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    onRemove() {
        window.removeEventListener('resize', this._onWindowResize);
        if (this._socket) {
            this._socket.onclose = null;
            this._socket.close();
            this._socket = null;
        }
        return super.onRemove();
    }

    //-------------------------------------------------//
    // WebSocket (sdc_ws/ai, SDCAiConsumer)            //
    //-------------------------------------------------//

    _connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        this._socket = new WebSocket(`${protocol}://${window.location.host}/sdc_ws/ai`);
        this._socket.onopen = () => this._setStatus('');
        this._socket.onmessage = (e) => this._onMessage(JSON.parse(e.data));
        this._socket.onclose = () => {
            this._socket = null;
            this._setStatus('disconnected');
        };
    }

    _send(data) {
        if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
            this._addMessage('error', 'The assistant is not connected. Please reload the page.');
            return false;
        }
        this._socket.send(JSON.stringify(data));
        return true;
    }

    _sendPrompt() {
        const $textarea = this.find('.ai-prompt-form textarea');
        const prompt = ($textarea.val() || '').trim();
        if (!prompt) {
            return;
        }
        this._requestId += 1;
        if (this._send({event: 'prompt', id: this._requestId, prompt})) {
            $textarea.val('');
            this._addMessage('user', prompt);
            this._$answer = null;
            this._setStatus('thinking…');
        }
    }

    async _onMessage(data) {
        if (data.id !== undefined && data.id !== null && data.id !== this._requestId) {
            return;  // a late message of an older request
        }
        if (data.type === 'ai_config') {
            this._onConfig(data);
        } else if (data.type === 'ai_delta') {
            this._answerBubble().append(document.createTextNode(data.text));
            this._scrollDown();
        } else if (data.type === 'ai_actions') {
            // Text of the next round goes into a new bubble below the actions
            this._$answer = null;
            const results = await this._runActions(data.actions);
            this._send({event: 'action_results', id: data.id, results});
            this._setStatus('thinking…');
        } else if (data.type === 'ai_answer') {
            this._$answer = null;
            this._setStatus('');
        } else if (data.type === 'error') {
            // A partial answer of this request is discarded
            if (this._$answer) {
                this._$answer.remove();
                this._$answer = null;
            }
            this._addMessage('error', data.msg || data.header || 'Error');
            this._setStatus('');
            if (data.scope === 'settings') {
                // The saved values were rejected; the server still uses the previous ones
                this._savingSettings = false;
                this._showSettings(true);
            } else if (data.scope === 'token') {
                this._showSettings(true);
            }
        }
    }

    //-------------------------------------------------//
    // Settings menu (set_config / ai_config)          //
    //-------------------------------------------------//

    _onConfig(config) {
        this._config = config;
        this._renderSettings();
        if (this._savingSettings) {
            this._savingSettings = false;
            this._addMessage('action', `Settings saved (${config.model}).`);
        }
        if (config.editable && !this._restored) {
            this._restored = true;
            const stored = this._storedSettings();
            if (stored) {
                this._send({event: 'set_config', ...stored});
                return;
            }
        }
        // Without a key the assistant can't answer: open the menu right away
        if (config.editable && !config.has_token) {
            this._showSettings(true);
        }
    }

    _renderSettings() {
        const config = this._config || {};
        const $form = this.find('.ai-settings-form');
        this.find('.ai-settings-readonly').toggleClass('d-none', !!config.editable);
        this.find('.ai-settings-summary').text([config.provider, config.model].filter(Boolean).join(' · '));
        $form.find('.ai-settings-fields').toggleClass('d-none', !config.editable);
        $form.find('.ai-base-url').toggleClass('d-none', !config.allow_base_url);
        $form.find('.ai-clear-token').toggleClass('d-none', !config.has_token);
        for (const field of SETTING_FIELDS) {
            $form.find(`[name="${field}"]`).val(config[field] ?? '');
        }
        $form.find('[name="token"]').val('')
            .attr('placeholder', config.has_token ? 'Set (leave empty to keep it)' : 'Required');
        $form.find('[name="clear_token"]').prop('checked', false);
        $form.find('[name="remember"]').prop('checked', this._storedSettings() !== null);
    }

    _showSettings(show) {
        if (show) {
            this._renderSettings();
            this._setCollapsed(false);
        }
        this.find('.ai-settings-form').toggleClass('d-none', !show);
    }

    _saveSettings() {
        const $form = this.find('.ai-settings-form');
        const data = {};
        for (const field of SETTING_FIELDS.concat(['token'])) {
            data[field] = ($form.find(`[name="${field}"]`).val() || '').trim();
        }
        data.clear_token = $form.find('[name="clear_token"]').prop('checked');
        if (!this._send({event: 'set_config', ...data})) {
            return;
        }
        this._storeSettings($form.find('[name="remember"]').prop('checked') ? data : null);
        // The server answers with ai_config (saved) or an error (the menu opens again)
        this._savingSettings = true;
        this._showSettings(false);
    }

    _storedSettings() {
        try {
            const settings = JSON.parse(window.localStorage.getItem(SETTINGS_STORAGE_KEY) || 'null');
            if (!settings) {
                return null;
            }
            settings.token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY) || '';
            return settings;
        } catch (e) {
            return null;  // storage blocked or corrupt
        }
    }

    _storeSettings(data) {
        try {
            if (!data) {
                window.localStorage.removeItem(SETTINGS_STORAGE_KEY);
                window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
                return;
            }
            const {token, clear_token, ...settings} = data;
            window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
            if (clear_token) {
                window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            } else if (token) {
                window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
            }
        } catch (e) {
            // Storage blocked (private mode): the settings only apply to this page
        }
    }

    //-------------------------------------------------//
    // Actions                                         //
    //-------------------------------------------------//

    /**
     * Runs the actions in order and returns one result per action for the server.
     *
     * @param {Array<{tool_use_id: string, name: string, input: object}>} actions
     * @returns {Promise<Array<{tool_use_id: string, content: *, is_error: boolean}>>}
     */
    async _runActions(actions) {
        const results = [];
        for (const action of actions) {
            this._addMessage('action', this._describeAction(action));
            try {
                const handler = this._actions[action.name];
                if (!handler) {
                    throw new Error(`Unknown action ${action.name}`);
                }
                results.push({tool_use_id: action.tool_use_id, content: await handler(action.input), is_error: false});
            } catch (e) {
                const msg = e?.msg || e?.message || String(e);
                this._addMessage('error', msg);
                results.push({tool_use_id: action.tool_use_id, content: msg, is_error: true});
            }
        }
        return results;
    }

    _describeAction({name, input}) {
        switch (name) {
            case 'navigate':
                return `→ open ${input.path}`;
            case 'read_page':
                return '→ read the page';
            case 'fill_form':
                return `→ fill in ${Object.keys(input.values || {}).join(', ')}`;
            case 'model_get':
                return `→ read ${input.model} #${input.id}`;
            case 'model_load':
                return `→ load ${input.model}`;
            default:
                return `→ ${name}`;
        }
    }

    async _navigate({path}) {
        trigger('goTo', path);
        // Wait until the navigator has loaded the new view
        const start = Date.now();
        await new Promise((resolve) => setTimeout(resolve, 100));
        while (window.sdcNav?._is_processing && Date.now() - start < NAVIGATION_TIMEOUT_MS) {
            await new Promise((resolve) => setTimeout(resolve, 100));
        }
        return `Now at ${window.location.pathname}`;
    }

    /**
     * Runs ``fn`` with a queryset of ``model`` that is closed afterwards.
     */
    async _withQuerySet(model, filter, fn) {
        const querySet = new SdcQuerySet(model, filter || {});
        try {
            return await fn(querySet);
        } finally {
            querySet.close();
        }
    }

    _record(instance) {
        return instance ? {id: instance.id, ...instance.toJson()} : null;
    }

    _modelLoad({model, filter}) {
        return this._withQuerySet(model, filter, async (querySet) => {
            await querySet.load();
            const records = querySet.valuesList.map((x) => this._record(x));
            return {
                count: records.length,
                records: records.slice(0, MAX_LOADED_RECORDS),
                truncated: records.length > MAX_LOADED_RECORDS,
            };
        });
    }

    _modelGet({model, id}) {
        return this._withQuerySet(model, {id}, async (querySet) => {
            await querySet.load();
            const record = querySet.byId(id);
            if (!record) {
                throw new Error(`${model} #${id} does not exist or the user may not see it`);
            }
            return this._record(record);
        });
    }

    //-------------------------------------------------//
    // Page: read_page / fill_form                     //
    //-------------------------------------------------//

    /**
     * Forms of the page without the assistant's own and without those of inactive views: the navigator keeps
     * previous views (e.g. after opening the current view again) hidden in the page, and their forms are exact
     * copies of the visible ones. read_page and fill_form use the same indexes.
     */
    _pageForms() {
        return [...document.forms].filter((form) => !form.closest('sdc-ai-assistant') && this._inActiveView(form));
    }

    /** False if the element lives in a navigator view container that is not active. */
    _inActiveView(el) {
        for (let box = el.closest('.sdc_sub_detail_container'); box;
             box = box.parentElement?.closest('.sdc_sub_detail_container')) {
            if (!box.classList.contains('active')) {
                return false;
            }
        }
        return true;
    }

    _readPage() {
        const html = this._simplifiedHtml();
        return {
            url: window.location.pathname,
            title: document.title,
            html: html.slice(0, MAX_PAGE_HTML),
            html_truncated: html.length > MAX_PAGE_HTML,
            forms: this._pageForms().map((form, index) => this._describeForm(form, index)),
        };
    }

    /** The visible body without scripts, styles, the assistant itself and most attributes. */
    _simplifiedHtml() {
        // Hidden elements are marked in the live page (only there their visibility is known) and removed in a copy
        const hidden = [...document.body.querySelectorAll('*')].filter((el) => !el.getClientRects().length
            && !['OPTION', 'BR'].includes(el.tagName));
        hidden.forEach((el) => el.setAttribute('data-ai-hidden', ''));
        const copy = document.body.cloneNode(true);
        hidden.forEach((el) => el.removeAttribute('data-ai-hidden'));

        copy.querySelectorAll(`${PAGE_SKIPPED}, [data-ai-hidden]`).forEach((el) => el.remove());
        const walker = document.createTreeWalker(copy, NodeFilter.SHOW_COMMENT);
        const comments = [];
        while (walker.nextNode()) {
            comments.push(walker.currentNode);
        }
        comments.forEach((c) => c.remove());
        copy.querySelectorAll('*').forEach((el) => {
            for (const {name} of [...el.attributes]) {
                if (!PAGE_ATTRIBUTES.includes(name.toLowerCase())) {
                    el.removeAttribute(name);
                }
            }
            if (SECRET_TYPES.includes((el.getAttribute('type') || '').toLowerCase())) {
                el.removeAttribute('value');
            }
        });
        return copy.innerHTML.replace(/\s+/g, ' ').replace(/> </g, '><').trim();
    }

    _describeForm(form, index) {
        const fields = {};
        for (const el of form.elements) {
            const type = this._fieldType(el);
            if (!el.name || ['submit', 'button', 'reset', 'image', 'fieldset'].includes(type)) {
                continue;
            }
            const field = fields[el.name] ??= {name: el.name, type, label: this._fieldLabel(el),
                required: el.required, disabled: el.disabled};
            if (SECRET_TYPES.includes(type)) {
                continue;  // name and type only, never the value
            }
            if (type === 'checkbox' || type === 'radio') {
                (field.options ??= []).push({value: el.value, label: this._fieldLabel(el), checked: el.checked});
                field.value = type === 'radio'
                    ? (field.options.find((o) => o.checked)?.value ?? null)
                    : field.options.filter((o) => o.checked).map((o) => o.value);
            } else if (el.tagName === 'SELECT') {
                field.multiple = el.multiple;
                field.options = [...el.options].slice(0, MAX_FIELD_OPTIONS).map((o) => ({value: o.value, label: o.text.trim()}));
                const selected = [...el.selectedOptions].map((o) => o.value);
                field.value = el.multiple ? selected : (selected[0] ?? null);
            } else {
                field.value = String(el.value ?? '').slice(0, MAX_FIELD_VALUE);
            }
        }
        // A single checkbox is a yes/no field
        for (const field of Object.values(fields)) {
            if (field.type === 'checkbox' && field.options?.length === 1) {
                field.value = field.options[0].checked;
                delete field.options;
            }
        }
        const pk = form.getAttribute('SdcModelPK');
        return {
            index,
            sdc_model_name: form.getAttribute('SdcModelName'),
            sdc_model_pk: pk === null ? null : Number(pk),
            visible: !!form.getClientRects().length,
            fields: Object.values(fields),
        };
    }

    _fieldType(el) {
        return el.tagName === 'SELECT' || el.tagName === 'TEXTAREA' || el.tagName === 'FIELDSET'
            ? el.tagName.toLowerCase() : (el.type || 'text').toLowerCase();
    }

    _fieldLabel(el) {
        const id = el.id && (window.CSS?.escape ? CSS.escape(el.id) : el.id.replace(/["\\]/g, '\\$&'));
        const label = (id && document.querySelector(`label[for="${id}"]`)) || el.closest('label');
        return (label?.innerText || label?.textContent || el.getAttribute('aria-label') || el.placeholder || '')
            .trim().slice(0, 100);
    }

    /**
     * Enters values like the user typing them. The form is never submitted. In SdcModel forms only `input` events
     * are fired: they update the form's model object, but not the `change` event that makes edit forms save
     * themselves, so the user still checks and saves the values.
     */
    _fillForm({form: index, values}) {
        const form = this._pageForms()[index];
        if (!form) {
            throw new Error(`There is no form ${index} on the page; use read_page to get the form indexes`);
        }
        const isModelForm = form.hasAttribute('SdcModelName');
        const set = {}, errors = {};
        for (const [name, value] of Object.entries(values || {})) {
            const fields = [...form.elements].filter((el) => el.name === name);
            const type = fields.length ? this._fieldType(fields[0]) : null;
            if (!fields.length) {
                errors[name] = 'no field with this name';
            } else if (SECRET_TYPES.includes(type)) {
                errors[name] = `${type} fields cannot be filled by the assistant`;
            } else if (fields.some((el) => el.disabled || el.readOnly)) {
                errors[name] = 'the field is disabled or read-only';
            } else {
                try {
                    const changed = this._setField(fields, type, value);
                    for (const el of changed) {
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        if (!isModelForm) {
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }
                    set[name] = this._describeForm(form, index).fields.find((f) => f.name === name)?.value;
                } catch (e) {
                    errors[name] = e.message;
                }
            }
        }
        if (Object.keys(set).length) {
            form.scrollIntoView?.({block: 'nearest', behavior: 'smooth'});
        }
        return {
            set,
            errors,
            ...(form.getClientRects().length ? {} : {warning: 'This form is not visible to the user.'}),
            note: isModelForm
                ? `SdcModel form (${form.getAttribute('SdcModelName')}): nothing is saved; the user has to check the values and submit or save the form.`
                : 'The form was not submitted; the user has to submit it.',
        };
    }

    /** Sets the value of a field (all elements with its name) and returns the elements that changed. */
    _setField(fields, type, value) {
        const matches = (el, v) => String(v) === el.value || String(v) === this._fieldLabel(el);
        if (type === 'checkbox') {
            if (fields.length === 1 && !Array.isArray(value)) {
                fields[0].checked = value === true || value === 'true' || value === 'on' || value === 1;
            } else {
                const wanted = Array.isArray(value) ? value : [value];
                fields.forEach((el) => {
                    el.checked = wanted.some((v) => matches(el, v));
                });
            }
            return fields;
        }
        if (type === 'radio') {
            const radio = fields.find((el) => matches(el, value));
            if (!radio) {
                throw new Error(`no option ${value}`);
            }
            radio.checked = true;
            return [radio];
        }
        if (type === 'select') {
            const select = fields[0];
            const wanted = Array.isArray(value) ? value : [value];
            const options = [...select.options];
            const isOption = (o, v) => String(v) === o.value || String(v) === o.text.trim();
            const missing = wanted.filter((v) => !options.some((o) => isOption(o, v)));
            if (missing.length) {
                throw new Error(`no option ${missing.join(', ')}`);
            }
            if (select.multiple) {
                options.forEach((o) => {
                    o.selected = wanted.some((v) => isOption(o, v));
                });
            } else {
                select.value = options.find((o) => isOption(o, wanted[0])).value;
            }
            return [select];
        }
        fields[0].value = value === null || value === undefined ? '' : String(value);
        return [fields[0]];
    }

    //-------------------------------------------------//
    // Window: move, resize, dock                      //
    //-------------------------------------------------//

    _setUpWindow() {
        const container = this.find('.ai-conversation-container')[0];
        const header = this.find('.ai-header')[0];
        try {
            this._geometry = JSON.parse(window.localStorage.getItem(WINDOW_STORAGE_KEY) || 'null');
        } catch (e) {
            this._geometry = null;  // storage blocked or corrupt: docked
        }
        // Pointer events cover mouse, pen and touch; the SDC event list has no pointer events
        header.addEventListener('pointerdown', (ev) => {
            // The header's buttons keep working
            if (!ev.target.closest('button, input, select, a')) {
                this._startPointerAction(ev, null);
            }
        });
        // A double click docks the window at the right edge again
        header.addEventListener('dblclick', (ev) => {
            if (!ev.target.closest('button')) {
                this._saveGeometry(null);
            }
        });
        for (const dir of ['n', 'e', 's', 'w', 'ne', 'nw', 'se', 'sw']) {
            const handle = document.createElement('div');
            handle.className = `ai-resize ai-resize-${dir}`;
            handle.setAttribute('aria-hidden', 'true');
            handle.addEventListener('pointerdown', (ev) => this._startPointerAction(ev, dir));
            container.appendChild(handle);
        }
        window.addEventListener('resize', this._onWindowResize);
        this._applyGeometry();
    }

    _setCollapsed(collapsed) {
        this.find('.ai-conversation-container').toggleClass('collapsed', collapsed);
        // The collapsed tab always sits at the right edge; the moved window comes back when expanded
        this._applyGeometry();
    }

    /**
     * Moves (``dir`` null) or resizes (``dir``: edges such as "n", "se") the window while the pointer is down.
     * The first move or resize turns the docked panel into a floating window.
     */
    _startPointerAction(ev, dir) {
        const $container = this.find('.ai-conversation-container');
        if (ev.button !== 0 || $container.hasClass('collapsed')) {
            return;
        }
        ev.preventDefault();
        const rect = $container[0].getBoundingClientRect();
        const start = {x: ev.clientX, y: ev.clientY, left: rect.left, top: rect.top, width: rect.width, height: rect.height};
        $container.addClass('dragging');

        const onMove = (e) => {
            const dx = e.clientX - start.x, dy = e.clientY - start.y;
            let {left, top, width, height} = start;
            if (!dir) {
                left += dx;
                top += dy;
            } else {
                if (dir.includes('e')) width += dx;
                if (dir.includes('s')) height += dy;
                if (dir.includes('w')) {
                    // The right edge stays where it is
                    width = Math.max(MIN_WINDOW_WIDTH, width - dx);
                    left = start.left + start.width - width;
                }
                if (dir.includes('n')) {
                    height = Math.max(MIN_WINDOW_HEIGHT, height - dy);
                    top = start.top + start.height - height;
                }
            }
            this._geometry = {left, top, width, height};
            this._applyGeometry();
        };
        const onUp = () => {
            document.removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerup', onUp);
            document.removeEventListener('pointercancel', onUp);
            $container.removeClass('dragging');
            this._saveGeometry(this._geometry);
        };
        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
    }

    /** Keeps the window inside the viewport and at least ``MIN_WINDOW_*`` large. */
    _clampGeometry({left, top, width, height}) {
        const maxWidth = window.innerWidth, maxHeight = window.innerHeight;
        width = Math.min(Math.max(width, Math.min(MIN_WINDOW_WIDTH, maxWidth)), maxWidth);
        height = Math.min(Math.max(height, Math.min(MIN_WINDOW_HEIGHT, maxHeight)), maxHeight);
        return {
            width, height,
            left: Math.min(Math.max(left, 0), maxWidth - width),
            top: Math.min(Math.max(top, 0), maxHeight - height),
        };
    }

    _applyGeometry() {
        const $container = this.find('.ai-conversation-container');
        if (!$container.length) {
            return;
        }
        const floating = this._geometry && !$container.hasClass('collapsed');
        $container.toggleClass('floating', !!floating);
        if (!floating) {
            $container.css({left: '', top: '', width: '', height: '', right: ''});
            return;
        }
        this._geometry = this._clampGeometry(this._geometry);
        const {left, top, width, height} = this._geometry;
        $container.css({left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px`, right: 'auto'});
    }

    _saveGeometry(geometry) {
        this._geometry = geometry;
        this._applyGeometry();
        try {
            if (geometry) {
                window.localStorage.setItem(WINDOW_STORAGE_KEY, JSON.stringify(this._geometry));
            } else {
                window.localStorage.removeItem(WINDOW_STORAGE_KEY);
            }
        } catch (e) {
            // Storage blocked (private mode): the position only applies to this page
        }
    }

    //-------------------------------------------------//
    // View                                            //
    //-------------------------------------------------//

    _addMessage(kind, text) {
        // Text only (never HTML): the content comes from the user and the model
        const $msg = $('<div>').addClass(`ai-message ${kind === 'error' ? 'assistant error' : kind}`).text(text);
        this.find('.ai-messages').append($msg);
        this._scrollDown();
        return $msg;
    }

    _answerBubble() {
        if (!this._$answer) {
            this._$answer = this._addMessage('assistant', '');
        }
        return this._$answer;
    }

    _scrollDown() {
        const $messages = this.find('.ai-messages');
        $messages.scrollTop($messages.prop('scrollHeight'));
    }

    _setStatus(text) {
        this.find('.ai-status').text(text);
    }

}

app.register(SdcAiAssistantController, false);
