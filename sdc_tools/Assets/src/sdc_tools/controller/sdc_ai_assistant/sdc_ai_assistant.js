import {AbstractSDC, app, SdcQuerySet, trigger} from 'sdc_client';

// Records returned to the model by one model_load action
const MAX_LOADED_RECORDS = 50;
// How long a navigate action waits for the new view
const NAVIGATION_TIMEOUT_MS = 10000;
// "Remember on this device": settings without the key in localStorage, the key only in sessionStorage
const SETTINGS_STORAGE_KEY = 'sdc_ai_settings';
const TOKEN_STORAGE_KEY = 'sdc_ai_token';
const SETTING_FIELDS = ['provider', 'base_url', 'model', 'effort', 'max_tokens'];


/**
 * Chat panel of the AI assistant, fixed at the right edge of the page; only rendered when the project sets `SDC_AI_ASSISTANT`.
 *
 * - The user types a question; the answer streams in. The assistant can also act on the page: open views like a
 *   navigation link and load, create, update or delete SdcModel records, always with the logged-in user's permissions.
 * - Every deletion asks the user for confirmation in a browser dialog first.
 * - Depending on the project settings it requires a login, and either uses the server's API key or the user's own.
 * - "⚙" opens the settings: with the server's key they only show the model in use; otherwise the user enters their
 *   API key and may choose the provider (Anthropic or any OpenAI-compatible API such as the KIT KI-Toolbox) and set
 *   the API URL (https, public hosts only), model, effort and max tokens. Changing the provider starts a new
 *   conversation. "Remember on this device" keeps the settings in the browser, the key only until the tab is closed.
 * - The "⇆" button collapses the panel to the edge of the page and expands it again.
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

        // Actions the assistant may run (tool names of SDCAiConsumer, see sdc_core/consumers.py)
        this._actions = {
            navigate: (input) => this._navigate(input),
            model_load: (input) => this._modelLoad(input),
            model_create: (input) => this._modelCreate(input),
            model_update: (input) => this._modelUpdate(input),
            model_delete: (input) => this._modelDelete(input),
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
                    this.find('.ai-conversation-container').toggleClass('collapsed');
                },
                '.ai-conversation-container': ($elm) => $elm.hasClass('collapsed') && $elm.removeClass('collapsed'),
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
            this._connect();
        }
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    onRemove() {
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
            this.find('.ai-conversation-container').removeClass('collapsed');
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
            case 'model_load':
                return `→ load ${input.model}`;
            case 'model_create':
                return `→ create ${input.model}`;
            case 'model_update':
                return `→ update ${input.model} #${input.id}`;
            case 'model_delete':
                return `→ delete ${input.model} #${input.id}`;
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

    _modelCreate({model, data}) {
        return this._withQuerySet(model, {}, async (querySet) => {
            const res = await querySet.create(data);
            return {created: this._record(res.data.instance)};
        });
    }

    _modelUpdate({model, id, data}) {
        return this._withQuerySet(model, {id}, async (querySet) => {
            await querySet.load();
            const record = querySet.byId(id);
            if (!record) {
                throw new Error(`${model} #${id} not found`);
            }
            // The edit form validates all fields: unchanged ones are sent as they are
            const [res] = await querySet.save({pk: id, data: {...record.serialize(), ...data}});
            return {saved: this._record(res.data.instance?.[0] ?? res.data.instance)};
        });
    }

    _modelDelete({model, id}) {
        if (!window.confirm(`The assistant wants to delete ${model} #${id}. Delete it?`)) {
            throw new Error('The user declined the deletion.');
        }
        return this._withQuerySet(model, {id}, async (querySet) => {
            await querySet.delete({pk: id});
            return `${model} #${id} deleted`;
        });
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
