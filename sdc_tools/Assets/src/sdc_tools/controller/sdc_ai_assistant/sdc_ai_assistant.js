import {AbstractSDC, app, SdcQuerySet, trigger} from 'sdc_client';
import {renderMarkdown} from './markdown.js';

// Records returned to the model by one model_load action
const MAX_LOADED_RECORDS = 50;
// How long a navigate action waits for the new view
const NAVIGATION_TIMEOUT_MS = 10000;
// Upper limit of every action: a hanging action (e.g. a model socket that never answers) returns an error result
const ACTION_TIMEOUT_MS = 30000;
// What a navigate action tells the model about an error view (sdc-error) by HTTP code
const ERROR_HINTS = {
    '404': 'this view does not exist',
    '403': 'the user may not open this view (not logged in or missing permissions)',
};
// read_page: size limits of what is sent to the model
const MAX_PAGE_HTML = 30000;
// read_page outline (default mode): condensed text of the page; lists are summarised (see _findLists)
const MAX_OUTLINE_TEXT = 4000;
const MAX_ROW_TEXT = 200;
// Rows of a list shown at once (read_page {scope: <list id>, rows: [from, to]} shows others)
const LIST_ROWS = 20;
// Repeated rows are summarised as a list above this number, or always when the list has a search/paging bar
const LIST_INLINE_MAX = 10;
// Block elements: the condensed text starts a new line before and after them
const TEXT_BLOCKS = new Set(['ADDRESS', 'ARTICLE', 'ASIDE', 'BLOCKQUOTE', 'BR', 'DD', 'DIV', 'DL', 'DT', 'FIELDSET',
    'FIGCAPTION', 'FIGURE', 'FOOTER', 'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEADER', 'HR', 'LEGEND', 'LI',
    'MAIN', 'NAV', 'OL', 'P', 'PRE', 'SECTION', 'TABLE', 'TBODY', 'TD', 'TH', 'THEAD', 'TR', 'UL']);
const MAX_FIELD_VALUE = 500;
const MAX_FIELD_OPTIONS = 50;
// read_page: attributes kept in the simplified HTML (all others are removed)
const PAGE_ATTRIBUTES = ['id', 'name', 'type', 'href', 'value', 'placeholder', 'for', 'role', 'aria-label', 'title',
    'sdc_click', 'sdcmodelname', 'sdcmodelpk', 'checked', 'selected', 'disabled', 'required', 'multiple',
    'data-ai-element'];
// read_page / click: elements the assistant can click (see _pageElements); they and the forms carry stable ids
const CLICKABLE = 'a[href], button, [sdc_click], [role=button], input[type=button], input[type=submit], '
    + 'input[type=reset]';
const MAX_PAGE_ELEMENTS = 200;
// Buttons that may delete, save, send data or log out: clicked only after the user allowed it in the chat
const CONFIRM_CLICK = /log ?out|sign ?out|delete|remove|destroy|drop|reset|submit|save|send|abmelden|löschen|entfernen|speichern|senden/i;
// How long a click waits before it checks whether the page is still loading
const CLICK_SETTLE_MS = 300;
// sdc-update-on-change ignores changes shortly after a view is rendered (_isNotReady); wait at most this long
const READY_MAX_MS = 1500;
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
 *   logged-in user's permissions: open views like a navigation link, read the current page, enter values into
 *   its forms (also the search bar of `<sdc-search-view>`, which filters its list at once), click buttons and
 *   links, and read SdcModel records.
 * - The assistant never submits a form: it fills forms (SdcModel forms are marked by `SdcModelName` /
 *   `SdcModelPK`) and the user checks and submits or saves them. Before it clicks a button that may delete, save
 *   or send data or log out, the chat asks the user to allow it. Links that leave the app are not clicked. It
 *   never reads or fills password, hidden or file fields.
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
        // A request is running (from the prompt until its ai_answer or error): no new prompt until it ends
        this._busy = false;
        // Answer bubble the streamed text of the current request goes into, and its Markdown source
        this._$answer = null;
        this._answerText = '';
        this._renderScheduled = false;
        // Connection settings reported by the server (ai_config)
        this._config = null;
        // Remembered settings are sent once per connection
        this._restored = false;
        // A set_config of the settings menu waits for the server's answer
        this._savingSettings = false;
        // {left, top, width, height} once the user moved or resized the window; null = docked at the right edge
        this._geometry = null;
        this._onWindowResize = () => this._applyGeometry();
        // Stable ids of the elements and forms shown to the model: the same DOM node keeps its id across read_page
        // calls, so a re-render of other parts of the page does not change what an id refers to (see _idOf)
        this._ids = new WeakMap();
        this._nodesById = new Map();
        this._nextId = 1;

        // Actions the assistant may run (tool names of SDCAiConsumer, see sdc_core/consumers.py)
        // SdcModels are read-only: there are no actions to create, change or delete records
        this._actions = {
            navigate: (input) => this._navigate(input),
            read_page: (input) => this._readPage(input),
            fill_form: (input) => this._fillForm(input),
            click: (input) => this._click(input),
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
            this._setBusy(false);
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
        if (this._busy) {
            // The server would cancel the running actions while the browser still runs them
            this._setStatus('please wait for the answer…');
            return;
        }
        this._requestId += 1;
        if (this._send({event: 'prompt', id: this._requestId, prompt})) {
            $textarea.val('');
            this._addMessage('user', prompt);
            this._$answer = null;
            this._setBusy(true);
            this._setStatus('thinking…');
        }
    }

    _setBusy(busy) {
        this._busy = busy;
        this.find('.ai-prompt-form [type="submit"]').prop('disabled', busy);
    }

    async _onMessage(data) {
        if (data.id !== undefined && data.id !== null && data.id !== this._requestId) {
            return;  // a late message of an older request
        }
        if (data.type === 'ai_config') {
            this._onConfig(data);
        } else if (data.type === 'ai_delta') {
            this._answerBubble();
            this._answerText += data.text;
            this._scheduleRender();
        } else if (data.type === 'ai_actions') {
            // Text of the next round goes into a new bubble below the actions
            this._finishAnswer();
            const results = await this._runActions(data.actions, data.id);
            if (results === null) {
                return;  // the request ended (disconnected or replaced) while its actions ran
            }
            this._send({event: 'action_results', id: data.id, results});
            this._setStatus('thinking…');
        } else if (data.type === 'ai_answer') {
            this._finishAnswer();
            this._setBusy(false);
            this._setStatus('');
        } else if (data.type === 'error') {
            // A partial answer of this request is discarded
            if (this._$answer) {
                this._$answer.remove();
                this._$answer = null;
            }
            this._addMessage('error', data.msg || data.header || 'Error');
            if (data.id === this._requestId) {
                this._setBusy(false);
            }
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
     * Stops (and returns null) as soon as request ``id`` is no longer the current one or the connection is gone,
     * so no action runs on a page the server no longer expects.
     *
     * @param {Array<{tool_use_id: string, name: string, input: object}>} actions
     * @param {number} id request the actions belong to
     * @returns {Promise<Array<{tool_use_id: string, content: *, is_error: boolean}>|null>}
     */
    async _runActions(actions, id = this._requestId) {
        const results = [];
        for (const action of actions) {
            if (id !== this._requestId || !this._socket) {
                return null;
            }
            this._addMessage('action', this._describeAction(action));
            try {
                const handler = this._actions[action.name];
                if (!handler) {
                    throw new Error(`Unknown action ${action.name}`);
                }
                // The user's answer is not limited by the action timeout
                const question = this._confirmationFor(action);
                if (question) {
                    const allowed = await this._confirm(question, id);
                    if (id !== this._requestId || !this._socket) {
                        return null;
                    }
                    if (!allowed) {
                        throw new Error('The user did not allow this click. Do not try it again unless the user '
                            + 'asks for it.');
                    }
                }
                const content = await this._withTimeout(handler(action.input), action.name);
                results.push({tool_use_id: action.tool_use_id, content, is_error: false});
            } catch (e) {
                const msg = e?.msg || e?.message || String(e);
                this._addMessage('error', msg);
                results.push({tool_use_id: action.tool_use_id, content: msg, is_error: true});
            }
        }
        return results;
    }

    /** Rejects if ``promise`` does not settle within ``this._actionTimeoutMs`` (default ``ACTION_TIMEOUT_MS``). */
    _withTimeout(promise, name) {
        const ms = this._actionTimeoutMs ?? ACTION_TIMEOUT_MS;
        let timer;
        const timeout = new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error(
                `${name} did not finish within ${ms / 1000}s; check the input and do not repeat it unchanged`)), ms);
        });
        return Promise.race([Promise.resolve(promise), timeout]).finally(() => clearTimeout(timer));
    }

    _describeAction({name, input}) {
        switch (name) {
            case 'navigate':
                return `→ open ${input.path}`;
            case 'read_page':
                return '→ read the page';
            case 'fill_form':
                return `→ fill in ${Object.keys(input.values || {}).join(', ')}`;
            case 'click': {
                const el = this._nodesById.get(input.element)?.deref();
                return `→ click ${el ? `"${this._elementText(el) || el.tagName.toLowerCase()}"` : `element ${input.element}`}`;
            }
            case 'model_get':
                return `→ read ${input.model} #${input.id}`;
            case 'model_load':
                return `→ load ${input.model}`;
            default:
                return `→ ${name}`;
        }
    }

    /**
     * Opens ``path`` and waits for the new view. Fails (the model gets an error result) if the view shows an error
     * page, e.g. ``sdc-error 404`` for a path that does not exist or ``403`` for a view the user may not open, or
     * if it does not finish loading in time.
     */
    async _navigate({path}) {
        this._goTo(path);
        await this._waitForPage();
        return `Now at ${this._checkLoadedView(path)}`;
    }

    /** Navigates with the sdc-navigator (``sdcNav.goTo``), else with the ``goTo`` event. */
    _goTo(path) {
        if (typeof window.sdcNav?.goTo === 'function') {
            window.sdcNav.goTo(path);
        } else {
            trigger('goTo', path);
        }
    }

    /** True while the navigator loads a view. */
    _loading() {
        return !!(window.sdcNav?._is_processing || document.querySelector('.sdc_sub_detail_container.loading'));
    }

    /** Waits ``minMs``, then until the navigator has loaded the view (at most ``NAVIGATION_TIMEOUT_MS``). */
    async _waitForPage(minMs = 100) {
        const start = Date.now();
        await new Promise((resolve) => setTimeout(resolve, minMs));
        while (this._loading() && Date.now() - start < NAVIGATION_TIMEOUT_MS) {
            await new Promise((resolve) => setTimeout(resolve, 100));
        }
    }

    /** The current path; throws if the view shows an error page or is still loading. */
    _checkLoadedView(target) {
        const at = window.location.pathname;
        const codes = this._errorViews();
        if (codes.length) {
            throw new Error(`Navigation to ${target} failed: the view shows an error page (${codes.map((c) => ERROR_HINTS[c]
                ? `${c}: ${ERROR_HINTS[c]}` : c || 'error').join('; ')}). Now at ${at}. Use only paths and arguments `
                + 'from the context or from links on the page.');
        }
        if (this._loading()) {
            throw new Error(`The view did not finish loading within ${NAVIGATION_TIMEOUT_MS / 1000}s. Now at ${at}.`);
        }
        return at;
    }

    /**
     * Resolves an SDC link (absolute, relative such as ``..~view`` or ``.~child~&pk=3``) against the current path
     * with the functions of the sdc-navigator (``_prepareUrl`` / ``_handleUrl``), as a click on the link would.
     *
     * @return {{href: string, path: string[], args: object}|null} null without navigator or for an invalid href
     */
    _resolveSdcHref(href) {
        const nav = window.sdcNav;
        if (!nav || typeof nav._handleUrl !== 'function' || !href) {
            return null;
        }
        // _handleUrl remembers the page prefix of absolute paths; resolving must not change the navigator
        const prefix = nav._non_controller_path_prefix;
        try {
            const state = nav._handleUrl(nav._prepareUrl(href));
            return {href: state.href, path: [...state.path], args: {...state.args}};
        } catch (e) {
            return null;
        } finally {
            nav._non_controller_path_prefix = prefix;
        }
    }

    /**
     * HTTP codes of the error views (``<sdc-error>``) in the active views, outside the assistant. The navigator
     * inserts them with a suffixed tag, e.g. ``<sdc-error_sdc-navigation-client data-code="404">``.
     */
    _errorViews() {
        return [...document.body.querySelectorAll('*')]
            .filter((el) => el.tagName.startsWith('SDC-ERROR') && !el.closest('sdc-ai-assistant')
                && this._inActiveView(el))
            .map((el) => String(el.getAttribute('data-code') ?? $(el).data('code') ?? ''));
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
            // The server sends at most one record more than needed: enough to know that there are more
            await querySet.load(null, {limit: MAX_LOADED_RECORDS + 1});
            const records = querySet.valuesList.slice(0, MAX_LOADED_RECORDS).map((x) => this._record(x));
            return {
                count: records.length,
                records,
                truncated: querySet.valuesList.length > MAX_LOADED_RECORDS,
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
     * copies of the visible ones. Fields outside any form (e.g. `<sdc-password-forgotten>`, the search bar of
     * `<sdc-search-view>`) follow as one entry per controller element. A form is identified by the stable id
     * (``_idOf``) of its form element, a group of loose fields by the id of its controller element.
     *
     * @return {{form: HTMLFormElement|null, container: Element, elements: Element[]}[]}
     */
    _pageForms() {
        const onPage = (el) => !el.closest('sdc-ai-assistant') && this._inActiveView(el);
        const forms = [...document.forms].filter(onPage)
            .map((form) => ({form, container: form, elements: [...form.elements]}));
        const loose = new Map();
        for (const el of document.body.querySelectorAll('input, select, textarea')) {
            if (el.form || !onPage(el)) {
                continue;
            }
            const container = this._controllerOf(el);
            if (!loose.has(container)) {
                loose.set(container, {form: null, container, elements: []});
            }
            loose.get(container).elements.push(el);
        }
        return forms.concat([...loose.values()]);
    }

    /** The nearest SDC controller element around ``el`` (or a custom element), else the body. */
    _controllerOf(el) {
        for (let node = el.parentElement; node && node !== document.body; node = node.parentElement) {
            if (node.classList.contains('_sdc_controller_') || node.tagName.includes('-')) {
                return node;
            }
        }
        return document.body;
    }

    /** The controller's tag; the navigator renames view elements (``<x-view_sdc-navigation-client>``). */
    _controllerTag(node) {
        return $(node).data('_controller_')?._tagName || node.tagName.toLowerCase();
    }

    _isVisible(entry) {
        return entry.form ? !!entry.form.getClientRects().length
            : entry.elements.some((el) => el.getClientRects().length);
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

    /**
     * read_page. ``mode`` ``outline`` (default): condensed text with ``[#id label]`` markers for clickable
     * elements, summarised lists (``_findLists``), forms and elements; ``html``: the simplified HTML as well.
     * ``scope``: an element, form or list id, or a controller tag, limits the result to that part of the page;
     * ``rows`` ``[from, to]`` (1-based) chooses the rows shown of the lists.
     */
    _readPage({mode = 'outline', scope = null, rows = null} = {}) {
        if (!['outline', 'html'].includes(mode)) {
            throw new Error('mode must be "outline" or "html"');
        }
        const root = this._scopeRoot(scope);
        const inRoot = (el) => root === document.body || root.contains(el);
        const elements = this._pageElements().filter(inRoot);
        const lists = this._findLists(root);
        const inRow = (el) => lists.some((l) => l.rows.some((r) => r.contains(el)));
        const result = {
            url: window.location.pathname,
            title: document.title,
            ...(scope !== null && scope !== undefined ? {scope} : {}),
        };
        if (mode === 'html') {
            const html = this._simplifiedHtml(elements, root);
            result.html = html.slice(0, MAX_PAGE_HTML);
            result.html_truncated = html.length > MAX_PAGE_HTML;
        } else {
            const text = this._condensedText(root, elements, lists);
            result.text = text.slice(0, MAX_OUTLINE_TEXT);
            if (text.length > MAX_OUTLINE_TEXT) {
                result.text_truncated = true;
            }
        }
        result.lists = lists.map((l) => this._describeList(l, rows));
        result.forms = this._pageForms().filter((f) => inRoot(f.container)).map((form) => this._describeForm(form));
        // Elements of list rows are listed with their row
        const shown = elements.filter((el) => mode === 'html' || !inRow(el));
        result.elements = shown.slice(0, MAX_PAGE_ELEMENTS).map((el) => this._describeElement(el))
            .filter((el) => el.visible);
        result.elements_truncated = shown.length > MAX_PAGE_ELEMENTS;
        if (document.querySelector('.modal.show')) {
            result.modal_open = true;
        }
        return result;
    }

    /**
     * The part of the page a read_page ``scope`` names: an id of an element, form or list, or a controller tag
     * (the navigator's suffixed view tags match too); none: the whole body.
     */
    _scopeRoot(scope) {
        if (scope === null || scope === undefined || scope === '') {
            return document.body;
        }
        if (typeof scope === 'number' || /^\d+$/.test(String(scope))) {
            const node = this._nodesById.get(Number(scope))?.deref();
            if (!node || !node.isConnected) {
                throw new Error(`There is no element, form or list ${scope} on the page; read the page again`);
            }
            return node;
        }
        const tag = String(scope).toLowerCase();
        const node = [...document.body.querySelectorAll('*')].find((el) => !el.closest('sdc-ai-assistant')
            && this._inActiveView(el) && (el.tagName.toLowerCase() === tag || this._controllerTag(el) === tag
                || el.tagName.toLowerCase().startsWith(`${tag}_`)));
        if (!node) {
            throw new Error(`There is no controller <${tag}> in the visible page`);
        }
        return node;
    }

    _visible(el) {
        return !!el.getClientRects().length;
    }

    /**
     * Repeated rows of the page: table rows, list items and runs of at least ``LIST_INLINE_MAX`` siblings with
     * the same tag and class (e.g. cards or ``<p>`` per record). Lists nested in a row of another list are part
     * of that row. A list counts only above ``LIST_INLINE_MAX`` visible rows, or with any row when its
     * controller has a search/paging bar (``<sdc-search-view>``).
     *
     * @return {{container: Element, rows: Element[], search: Element|null}[]}
     */
    _findLists(root) {
        const candidates = [];
        const usable = (el) => !el.closest(PAGE_SKIPPED) && this._inActiveView(el) && this._visible(el);
        // The scope itself may be a list
        const all = (selector) => [...(root.matches(selector) ? [root] : []), ...root.querySelectorAll(selector)];
        for (const table of all('table')) {
            candidates.push([table, [...table.querySelectorAll('tr')].filter((tr) => tr.closest('table') === table
                && !tr.closest('thead') && tr.querySelector('td'))]);
        }
        for (const list of all('ul, ol')) {
            candidates.push([list, [...list.children].filter((c) => c.tagName === 'LI')]);
        }
        for (const parent of all('*')) {
            if (parent.children.length < LIST_INLINE_MAX || ['TABLE', 'TBODY', 'UL', 'OL', 'SELECT'].includes(parent.tagName)) {
                continue;
            }
            const groups = new Map();
            for (const child of parent.children) {
                const key = `${child.tagName}.${typeof child.className === 'string' ? child.className : ''}`;
                groups.set(key, [...(groups.get(key) || []), child]);
            }
            for (const group of groups.values()) {
                if (group.length >= LIST_INLINE_MAX && group.length >= parent.children.length * 0.8) {
                    candidates.push([parent, group]);
                }
            }
        }
        const lists = [];
        for (const [container, all] of candidates) {
            const rows = all.filter(usable);
            if (!rows.length || !usable(container)) {
                continue;
            }
            const search = this._searchViewOf(container);
            if (rows.length > LIST_INLINE_MAX || search) {
                lists.push({container, rows, search});
            }
        }
        // A search bar belongs to the longest list of its controller; short lists beside it stay text
        const longest = new Map();
        for (const l of lists) {
            if (l.search && (longest.get(l.search)?.rows.length ?? -1) < l.rows.length) {
                longest.set(l.search, l);
            }
        }
        const kept = lists.filter((l) => !l.search || longest.get(l.search) === l || l.rows.length > LIST_INLINE_MAX);
        // The outermost list wins
        return kept.filter((l) => !kept.some((o) => o !== l && o.rows.some((r) => r.contains(l.container))));
    }

    /** The ``<sdc-search-view>`` of the controller that shows ``container`` (search and paging of the list). */
    _searchViewOf(container) {
        for (let node = container.parentElement; node && node !== document.body; node = node.parentElement) {
            const view = node.querySelector('sdc-search-view');
            if (view && this._inActiveView(view)) {
                return view;
            }
            if (node.classList.contains('_sdc_controller_')) {
                return null;
            }
        }
        return null;
    }

    /** Short description of an element for list rows: id, text and what the model needs to choose it. */
    _compactElement(el) {
        const d = this._describeElement(el);
        return {id: d.id, text: d.text, ...(d.href ? {href: d.href} : {}),
            ...(d.needs_confirmation ? {needs_confirmation: true} : {}),
            ...(d.clickable === false ? {clickable: false} : {})};
    }

    _describeList({container, rows, search}, range) {
        let [from, to] = Array.isArray(range) && range.length === 2 ? range.map(Number) : [1, LIST_ROWS];
        from = Math.max(1, from || 1);
        to = Math.min(rows.length, Math.max(from, to || from + LIST_ROWS - 1), from + 2 * LIST_ROWS - 1);
        const shown = rows.slice(from - 1, to).map((row, i) => {
            const elements = this._pageElements().filter((el) => row.contains(el) && this._visible(el));
            return {
                n: from + i,
                text: this._condensedText(row, [], [], false).replace(/\n+/g, ' | ').slice(0, MAX_ROW_TEXT),
                ...(elements.length ? {elements: elements.map((el) => this._compactElement(el))} : {}),
            };
        });
        const list = {
            id: this._idOf(container),
            kind: container.tagName === 'TABLE' ? 'table' : 'list',
            controller: this._controllerTag(this._controllerOf(container)),
            rows_in_page: rows.length,
            rows_shown: shown.length ? [shown[0].n, shown.at(-1).n] : [],
            rows: shown,
        };
        if (shown.length < rows.length) {
            list.more_rows = `read_page {scope: ${list.id}, rows: [from, to]} shows other rows of this page`;
        }
        if (search) {
            const entry = this._pageForms().find((e) => e.container === search || (e.form && search.contains(e.form)));
            const next = search.querySelector('.page-number-control-btn-next');
            const prev = search.querySelector('.page-number-control-btn-prev');
            const range = (search.querySelector('.range-span')?.textContent || '').trim();
            const total = Number((search.querySelector('.total-amount-span')?.textContent || '').replace(/[^\d]/g, ''));
            list.search = {
                ...(entry ? {form: this._formId(entry)} : {}),
                ...(range ? {range} : {}),
                ...(total ? {total} : {}),
                ...(next && this._visible(next) ? {next: this._idOf(next), next_disabled: this._isDisabled(next)} : {}),
                ...(prev && this._visible(prev) ? {prev: this._idOf(prev), prev_disabled: this._isDisabled(prev)} : {}),
                hint: 'Filter with fill_form on the search form (the list updates by itself); page with click on '
                    + 'next/prev; model_load reads records directly.',
            };
        }
        return list;
    }

    /**
     * The visible text of ``root`` with one line per block element, ``## `` before headings and
     * ``[#id label]`` for clickable ``elements``; ``lists`` are replaced by a one-line reference, form fields
     * are left out (they are in ``forms``).
     */
    _condensedText(root, elements = [], lists = [], marks = true) {
        const clickable = new Set(elements);
        const listOf = new Map(lists.map((l) => [l.container, l]));
        const parts = [];
        const walk = (node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                parts.push(node.nodeValue);
                return;
            }
            if (node.nodeType !== Node.ELEMENT_NODE) {
                return;
            }
            const el = node;
            if (el.matches(PAGE_SKIPPED) || ['INPUT', 'SELECT', 'TEXTAREA', 'OPTION'].includes(el.tagName)
                || (el.classList.contains('sdc_sub_detail_container') && !el.classList.contains('active'))
                || (!this._visible(el) && el.tagName !== 'BR')) {
                return;
            }
            const list = listOf.get(el);
            if (list) {
                parts.push(`\n[list #${this._idOf(el)}: ${list.rows.length} rows, see lists]\n`);
                return;
            }
            if (marks && clickable.has(el)) {
                parts.push(` [#${this._idOf(el)} ${this._elementText(el) || el.tagName.toLowerCase()}] `);
                return;
            }
            const block = TEXT_BLOCKS.has(el.tagName);
            if (block) {
                parts.push('\n');
            }
            if (/^H[1-4]$/.test(el.tagName)) {
                parts.push('## ');
            }
            for (const child of el.childNodes) {
                walk(child);
            }
            if (block) {
                parts.push('\n');
            }
        };
        walk(root);
        return parts.join('').replace(/[ \t\u00a0]+/g, ' ').replace(/ *\n[ \n]*/g, '\n').trim();
    }

    /**
     * The visible body (or ``root``) without scripts, styles, the assistant itself and most attributes.
     * Clickable elements carry ``data-ai-element`` with their id for ``click``.
     */
    _simplifiedHtml(elements = [], root = document.body) {
        // Hidden elements are marked in the live page (only there their visibility is known) and removed in a copy
        const hidden = [...document.body.querySelectorAll('*')].filter((el) => !el.getClientRects().length
            && !['OPTION', 'BR'].includes(el.tagName));
        hidden.forEach((el) => el.setAttribute('data-ai-hidden', ''));
        elements.forEach((el) => el.setAttribute('data-ai-element', String(this._idOf(el))));
        const copy = root.cloneNode(true);
        hidden.forEach((el) => el.removeAttribute('data-ai-hidden'));
        elements.forEach((el) => el.removeAttribute('data-ai-element'));

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
        const html = root === document.body ? copy.innerHTML : copy.outerHTML;
        return html.replace(/\s+/g, ' ').replace(/> </g, '><').trim();
    }

    /** The stable id of a form entry of ``_pageForms``: of its form element or of its controller element. */
    _formId(entry) {
        return this._idOf(entry.form || entry.container);
    }

    _describeForm(entry) {
        const fields = {};
        for (const el of entry.elements) {
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
        const pk = entry.form?.getAttribute('SdcModelPK') ?? null;
        return {
            id: this._formId(entry),
            sdc_model_name: entry.form?.getAttribute('SdcModelName') ?? null,
            sdc_model_pk: pk === null ? null : Number(pk),
            ...(entry.form ? {} : {form_element: false, controller: this._controllerTag(entry.container)}),
            ...(this._updatesOnChange(entry) ? {updates_on_change: true} : {}),
            visible: this._isVisible(entry),
            fields: Object.values(fields),
        };
    }

    /**
     * True for fields that update their view when they change (``timer-change`` of ``sdc-update-on-change``, e.g.
     * the search bar of ``<sdc-search-view>``). SdcModel forms use the same class to save themselves; they are
     * never changed by the assistant.
     */
    _updatesOnChange(entry) {
        return !entry.form?.hasAttribute('SdcModelName') && entry.elements.some((el) => el.classList.contains('timer-change'));
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
     * themselves, so the user still checks and saves the values. Fields outside a form get `input` and `change`
     * events like in other forms; the controller's buttons (which the assistant does not click) send them.
     */
    _fillForm({form: id, values}) {
        const entry = this._pageForms().find((e) => this._ids.get(e.form || e.container) === id);
        if (!entry) {
            throw new Error(`There is no form ${id} on the page (the page may have changed); use read_page to get `
                + 'the form ids');
        }
        const {form} = entry;
        const isModelForm = !!form?.hasAttribute('SdcModelName');
        const set = {}, errors = {};
        for (const [name, value] of Object.entries(values || {})) {
            const fields = entry.elements.filter((el) => el.name === name);
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
                    set[name] = this._describeForm(entry).fields.find((f) => f.name === name)?.value;
                } catch (e) {
                    errors[name] = e.message;
                }
            }
        }
        if (Object.keys(set).length) {
            (form || entry.elements[0]).scrollIntoView?.({block: 'nearest', behavior: 'smooth'});
        }
        let note = 'The form was not submitted; the user has to submit it.';
        if (isModelForm) {
            note = `SdcModel form (${form.getAttribute('SdcModelName')}): nothing is saved; the user has to check the values and submit or save the form.`;
        } else if (this._updatesOnChange(entry)) {
            note = 'Nothing was submitted. This view updates by itself when a value changes (e.g. a search bar '
                + 'filters its list); use read_page to see the result.';
        } else if (!form) {
            note = 'Nothing was submitted. Views that react to changes (e.g. a search bar) update by themselves; '
                + 'otherwise click the button of the view (see the elements of read_page).';
        }
        return {
            set,
            errors,
            ...(this._isVisible(entry) ? {} : {warning: 'This form is not visible to the user.'}),
            note,
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
    // Page: click (buttons and links)                 //
    //-------------------------------------------------//

    /**
     * Buttons and links of the active views (``CLICKABLE``) in document order, without the assistant's own.
     * read_page lists the visible ones with their stable id, the ``element`` of ``click``.
     *
     * @return {Element[]}
     */
    _pageElements() {
        return [...document.body.querySelectorAll(CLICKABLE)]
            .filter((el) => !el.closest('sdc-ai-assistant') && this._inActiveView(el));
    }

    /** The stable id of ``node``; a node seen for the first time gets the next number. */
    _idOf(node) {
        let id = this._ids.get(node);
        if (id === undefined) {
            id = this._nextId++;
            this._ids.set(node, id);
            // Weak: removed elements are freed; the id then reports that the element is gone
            this._nodesById.set(id, new WeakRef(node));
        }
        return id;
    }

    /**
     * The clickable element with the stable ``id``, or throws: unknown ids, elements that were removed or are in
     * a hidden view, and (with ``text``) elements whose text changed are refused, so a click never hits another
     * element than the one the model read.
     */
    _elementById(id, text) {
        const node = this._nodesById.get(id)?.deref();
        if (!node) {
            throw new Error(`There is no element ${id} on the page; use read_page to get the element ids`);
        }
        if (!node.isConnected || !this._pageElements().includes(node)) {
            throw new Error(`Element ${id} is no longer on the page (the page changed); read the page again`);
        }
        const current = this._elementText(node);
        if (text !== undefined && text !== null && current.toLowerCase() !== String(text).trim().toLowerCase()) {
            throw new Error(`Element ${id} is now "${current}", not "${text}" (the page changed); read the page again`);
        }
        return node;
    }

    _elementText(el) {
        return (el.innerText || el.textContent || el.value || el.getAttribute('aria-label') || el.title || '')
            .replace(/\s+/g, ' ').trim().slice(0, 80);
    }

    /**
     * The controller methods named in ``sdc_click``, without the ``this.event_…`` entries that SDC adds for
     * handlers of the controller's ``events`` list (e.g. ``this.event_.navigation-links``).
     */
    _elementHandlers(el) {
        return (el.getAttribute('sdc_click') || '').split(/\s+/).filter((h) => h && !h.startsWith('this.event_'));
    }

    /**
     * Where a link leads: ``{sdc: true, target}`` for SDC views (``.navigation-links`` and same-origin paths with
     * ``~``; ``target`` resolved by the navigator), ``{external: true, href}`` for links that leave the single page
     * app, null for in-page links (``#…``, ``javascript:``) and for elements that are no links.
     */
    _linkTarget(el) {
        if (el.tagName !== 'A' || !el.hasAttribute('href')) {
            return null;
        }
        // The navigator keeps the original (relative) href of its links
        const raw = $(el).data('_origin_href') || el.getAttribute('href');
        if (!raw || raw.startsWith('#') || raw.toLowerCase().startsWith('javascript:')) {
            return null;
        }
        if (el.classList.contains('navigation-links')) {
            return {sdc: true, href: raw, target: this._resolveSdcHref(raw)};
        }
        let url;
        try {
            url = new URL(raw, window.location.href);
        } catch (e) {
            return {external: true, href: raw};
        }
        const newTab = (el.getAttribute('target') || '_self') !== '_self' || el.hasAttribute('download');
        if (url.origin === window.location.origin && url.pathname.includes('~') && !newTab) {
            const path = url.pathname + url.search;
            return {sdc: true, href: path, target: this._resolveSdcHref(path)};
        }
        return {external: true, href: url.href};
    }

    _isDisabled(el) {
        return !!(el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled')
            || el.closest('fieldset[disabled]'));
    }

    /** Submit buttons of a form (also ``<button>`` without type, which submits too). */
    _submitsForm(el) {
        return !!el.form && el.type === 'submit' && (el.tagName === 'BUTTON' || el.tagName === 'INPUT');
    }

    /**
     * What a click on ``el`` may do: ``{blocked: reason}`` if the assistant must not click it,
     * ``{confirm: true}`` if the user has to allow it first, else ``{}``.
     */
    _clickPolicy(el) {
        if (!el.getClientRects().length) {
            return {blocked: 'the element is not visible'};
        }
        if (this._isDisabled(el)) {
            return {blocked: 'the element is disabled'};
        }
        if (this._submitsForm(el)) {
            return {blocked: 'it submits a form; forms are submitted by the user'};
        }
        if (this._linkTarget(el)?.external) {
            return {blocked: 'the link leaves the app; give the user the link instead'};
        }
        // Only shows or hides something (a modal, a collapsed menu): e.g. the "Remove" button of a list row opens
        // the modal with the real "Remove …" button, which then asks
        if (el.getAttribute('data-bs-toggle') && !this._elementHandlers(el).length && el.tagName !== 'A') {
            return {};
        }
        const text = [this._elementText(el), this._elementHandlers(el).join(' '), el.title || '',
            el.getAttribute('aria-label') || '', typeof el.className === 'string' ? el.className : '',
            el.type === 'reset' ? 'reset' : ''].join(' ');
        return CONFIRM_CLICK.test(text) ? {confirm: true} : {};
    }

    _describeElement(el) {
        const link = this._linkTarget(el);
        const policy = this._clickPolicy(el);
        const handlers = this._elementHandlers(el);
        return {
            id: this._idOf(el),
            kind: el.tagName === 'A' ? 'link' : 'button',
            text: this._elementText(el),
            controller: this._controllerTag(this._controllerOf(el)),
            ...(link?.sdc ? {href: link.target?.href ?? link.href} : {}),
            ...(link?.external ? {href: link.href, external: true} : {}),
            ...(handlers.length ? {handlers} : {}),
            ...(el.getAttribute('data-bs-toggle') ? {toggles: el.getAttribute('data-bs-toggle')} : {}),
            ...(policy.blocked ? {clickable: false, reason: policy.blocked} : {}),
            ...(policy.confirm ? {needs_confirmation: true} : {}),
            visible: !!el.getClientRects().length,
        };
    }

    /** The question shown to the user before the action runs, or null if it may run without asking. */
    _confirmationFor({name, input}) {
        if (name !== 'click') {
            return null;
        }
        let el;
        try {
            el = this._elementById(input?.element, input?.text);
        } catch (e) {
            return null;  // the click itself reports the error
        }
        if (!this._clickPolicy(el).confirm) {
            return null;
        }
        return `The assistant wants to click "${this._elementText(el) || el.tagName.toLowerCase()}". Allow it?`;
    }

    /**
     * Asks the user in the chat; resolves true (Allow) or false (Deny, or the request ended).
     *
     * @param {string} question
     * @param {number} id request the question belongs to
     * @returns {Promise<boolean>}
     */
    _confirm(question, id = this._requestId) {
        this._setCollapsed(false);
        this._setStatus('waiting for your answer…');
        return new Promise((resolve) => {
            const $msg = this._addMessage('action', question).addClass('ai-confirm');
            const $buttons = $('<div class="ai-confirm-buttons"></div>').appendTo($msg);
            let watch = null;
            const done = (allowed) => {
                clearInterval(watch);
                $buttons.remove();
                $msg.append(document.createTextNode(allowed ? ' Allowed.' : ' Not allowed.'));
                this._setStatus(allowed ? '' : 'thinking…');
                resolve(allowed);
            };
            $('<button type="button" class="btn btn-sm btn-primary ai-confirm-allow"></button>').text('Allow')
                .on('click', () => done(true)).appendTo($buttons);
            $('<button type="button" class="btn btn-sm btn-outline-secondary ai-confirm-deny"></button>').text('Deny')
                .on('click', () => done(false)).appendTo($buttons);
            // A new request or a lost connection answers "no"
            watch = setInterval(() => (id !== this._requestId || !this._socket) && done(false), 250);
            this._scrollDown();
        });
    }

    /**
     * Clicks a button or link of the current page (``element``: id from read_page, optional ``text`` to check that
     * it is still the same element) like the user. SDC links
     * open with the navigator's ``goTo``; buttons run their controller's handlers (``sdc_click``). Form submit
     * buttons and links leaving the app are never clicked; the user is asked before risky clicks (see
     * ``_runActions``).
     */
    async _click({element, text: expected}) {
        const el = this._elementById(element, expected);
        const text = this._elementText(el) || el.tagName.toLowerCase();
        const policy = this._clickPolicy(el);
        if (policy.blocked) {
            throw new Error(`"${text}" cannot be clicked: ${policy.blocked}.`);
        }
        const before = window.location.pathname + window.location.search;
        const modalBefore = !!document.querySelector('.modal.show');
        const link = this._linkTarget(el);
        el.scrollIntoView?.({block: 'nearest', behavior: 'smooth'});
        if (link?.sdc && !this._elementHandlers(el).length) {
            // Same as the navigator's link handler, also for links outside .navigation-links
            this._goTo(link.href);
        } else {
            el.click();
        }
        await this._waitForPage(CLICK_SETTLE_MS);
        const at = this._checkLoadedView(link?.sdc ? link.target?.href ?? link.href : `"${text}"`);
        const modal = !!document.querySelector('.modal.show');
        return {
            clicked: text,
            url: at,
            navigated: at + window.location.search !== before,
            ...(modal && !modalBefore ? {modal_opened: true} : {}),
            note: 'Use read_page to see the result.',
        };
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
        // Links to SDC views in answers open in the sdc-navigator instead of reloading the page
        this.find('.ai-messages')[0].addEventListener('click', (ev) => {
            const a = ev.target.closest('a.ai-md-nav');
            if (a && !ev.ctrlKey && !ev.metaKey && !ev.shiftKey && ev.button === 0) {
                ev.preventDefault();
                trigger('goTo', a.getAttribute('href'));
            }
        });
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
            this._$answer = this._addMessage('assistant', '').addClass('ai-markdown');
            this._answerText = '';
        }
        return this._$answer;
    }

    /** Renders the streamed Markdown at most once per frame (a long answer arrives in many small deltas). */
    _scheduleRender() {
        if (this._renderScheduled) {
            return;
        }
        this._renderScheduled = true;
        const frame = window.requestAnimationFrame || ((cb) => setTimeout(cb, 16));
        frame(() => {
            this._renderScheduled = false;
            this._renderAnswer();
        });
    }

    _renderAnswer() {
        if (this._$answer) {
            this._$answer[0].replaceChildren(renderMarkdown(this._answerText));
            this._scrollDown();
        }
    }

    /** Renders the complete answer of this round; later text starts a new bubble. */
    _finishAnswer() {
        this._renderAnswer();
        this._$answer = null;
        this._answerText = '';
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
