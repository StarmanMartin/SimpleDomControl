/**
 * @jest-environment jsdom
 */

import {AbstractSDC, app, test_utils, trigger} from 'sdc_client';
import {} from "#root/src/models/src.js";
import '../src/sdc_tools/sdc_tools.organizer.js';
import {SdcNavigatorController} from '../src/sdc_tools/controller/sdc_navigator/sdc_navigator.js';
import {matchesAllowedPaths} from '../src/sdc_tools/controller/sdc_navigation_client/sdc_navigation_client.js';
import {renderMarkdown} from '../src/sdc_tools/controller/sdc_ai_assistant/markdown.js';
import {jest} from '@jest/globals';


describe('SdcNavigator', () => {
    let controller,
        child = null;
    const textArg = 'DUMMY';

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-navigator',
            {'defaultController': `sdc-dummy?text=${textArg}`},
            '<div><h1 >Controller loading...</h1></div>');
    });

    test('Load Content', async () => {
        for (let i = 0; i < 100; ++i) {
            await new Promise(resolve => setTimeout(resolve, 50));
            if (controller._childController.sdcDummy && controller._childController.sdcDummy.length > 0) {
                child = controller._childController.sdcDummy[0];
                break;
            }
        }

        expect(child._text).toBe(textArg);
    });

    test('redirect takes priority over unfinished nested navigation and queued requests', async () => {
        await new Promise(resolve => setTimeout(resolve, 300));
        const container = () => $('<div></div>');
        controller._history_path = ['protected'];
        controller._origin_target = ['protected', 'unreachable'];
        controller._process_queue = [['/~queued', true]];
        controller._current_process = [controller._origin_target, {}];
        controller._preparedLastViewContainer = () => ({
            active_container: container(), active_sub_container: container(),
            empty_container: container(), deeper_sub_container: container(),
        });
        const goTo = jest.spyOn(controller, 'goTo').mockImplementation(() => {});
        const navigate = jest.spyOn(controller, 'navigateToPage');
        const redirected = {autoRedirect: '<a href=".~login~&next=..">Redirector</a>', controller_name: () => 'Protected'};

        controller.navLoaded(redirected);

        expect(navigate).not.toHaveBeenCalled();
        expect(goTo).toHaveBeenCalledTimes(1);
        expect(goTo.mock.calls[0][0]).toContain('.~login~&next=/~protected');
        expect(controller._process_queue).toEqual([['/~queued', true]]);
        expect(redirected.autoRedirect).toBeNull();
        expect(controller._is_processing).toBe(false);
        controller._process_queue = [];
        goTo.mockRestore();
        navigate.mockRestore();
    });

    test('a redirect while loading a nested route opens the destination once', async () => {
        await new Promise(resolve => setTimeout(resolve, 300));
        class RedirectTestController extends AbstractSDC {
            constructor() {
                super();
                this.contentUrl = '/redirect-test';
                this.contentReload = true;
            }
        }
        app.register(RedirectTestController);
        if (!app.tagNames.includes('redirect-test')) app.tagNames.push('redirect-test');
        const originalGet = $.get.bind($);
        const get = jest.spyOn($, 'get').mockImplementation((url, args) => {
            if (url === '/redirect-test') {
                return Promise.reject({status: 301, responseJSON: {
                    'url-link': '<a href=".~sdc-dummy~&text=Destination">Redirector</a>',
                }});
            }
            return originalGet(url, args);
        });
        const navigate = jest.spyOn(controller, 'navigateToPage');
        try {
            trigger('goTo', '/redirect-test/unreachable');
            await new Promise(resolve => setTimeout(resolve, 600));
            expect(controller.find('.sdc_sub_detail_container.active').last().text().trim()).toBe('Destination');
            expect(controller.$container.text()).not.toContain('Redirected');
            expect(get.mock.calls.filter(([url]) => url === '/redirect-test')).toHaveLength(1);
            expect(navigate.mock.calls.filter(([path]) => path.at(-1) === 'sdc-dummy')).toHaveLength(1);
        } finally {
            get.mockRestore();
            navigate.mockRestore();
        }
    });

    test('allowedPaths patterns', () => {
        expect(matchesAllowedPaths([], ['a', 'b'])).toBe(true);
        expect(matchesAllowedPaths(undefined, [])).toBe(true);
        expect(matchesAllowedPaths([[]], [])).toBe(true);
        expect(matchesAllowedPaths([[]], ['a'])).toBe(false);
        expect(matchesAllowedPaths([['*']], ['a'])).toBe(true);
        expect(matchesAllowedPaths([['*']], [])).toBe(false);
        expect(matchesAllowedPaths([['*']], ['a', 'b'])).toBe(false);
        expect(matchesAllowedPaths([['**', 'dashboard']], ['dashboard'])).toBe(true);
        expect(matchesAllowedPaths([['**', 'dashboard']], ['main', 'x', 'dashboard'])).toBe(true);
        expect(matchesAllowedPaths([['**', 'dashboard']], ['dashboard', 'x'])).toBe(false);
        expect(matchesAllowedPaths([['**', 'dashboard']], [])).toBe(false);
        expect(matchesAllowedPaths([['dashboard'], ['admin', '**']], ['admin', 'x', 'y'])).toBe(true);
        expect(matchesAllowedPaths([['dashboard', '*', 'list']], ['dashboard', 'x', 'list'])).toBe(true);
        expect(matchesAllowedPaths([['**']], [])).toBe(true);
    });

    test('a view opened outside its allowedPaths shows "Not allowed" (sdc-error 403)', async () => {
        await new Promise(resolve => setTimeout(resolve, 300));
        let allowedPaths = [];
        class AllowedPathTestController extends AbstractSDC {
            constructor() {
                super();
                this.contentUrl = '/allowed-path-test';
                this.contentReload = true;
                this.allowedPaths = allowedPaths;
            }
        }
        app.register(AllowedPathTestController);
        if (!app.tagNames.includes('allowed-path-test')) app.tagNames.push('allowed-path-test');
        const originalGet = $.get.bind($);
        const get = jest.spyOn($, 'get').mockImplementation((url, args) => url === '/allowed-path-test'
            ? Promise.resolve('<div class="allowed-view">Allowed view</div>') : originalGet(url, args));
        const error = jest.spyOn(console, 'error').mockImplementation(() => {});
        const active = () => controller.find('.0_sdc_sub_detail_container.active');
        try {
            // Only at the top: allowed
            allowedPaths = [[]];
            trigger('goTo', '/allowed-path-test');
            await new Promise(resolve => setTimeout(resolve, 400));
            expect(active().find('.allowed-view').text()).toBe('Allowed view');
            // Only below a dashboard: refused at the top
            allowedPaths = [['**', 'dashboard']];
            trigger('goTo', '/sdc-dummy', {text: 'Between'});
            await new Promise(resolve => setTimeout(resolve, 300));
            trigger('goTo', '/allowed-path-test');
            await new Promise(resolve => setTimeout(resolve, 600));
            expect(active().find('.allowed-view').length).toBe(0);
            expect(active().find('[data-code="403"]').length).toBe(1);
            expect(active().text()).toContain('Not allowed: allowed-path-test cannot be opened at /~allowed-path-test.');
            expect(controller._is_processing).toBe(false);
            expect(error).toHaveBeenCalledWith(expect.stringContaining('<allowed-path-test> is not allowed at /~allowed-path-test'));
        } finally {
            get.mockRestore();
            error.mockRestore();
        }
    });

    test('Navigate same level [A]', async () => {
        trigger('goTo', '/sdc-dummy', {text: 'DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY A');
    });

    test('Navigate same level [B]', async () => {
        trigger('goTo', ['/', 'sdc-dummy'], {text: 'DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY B');
    });

    test('Navigate same level [C]', async () => {
        trigger('goTo', ['', 'sdc-dummy'], {text: 'DUMMY C'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY C');
    });

    test('Navigate next level [A]', async () => {
        trigger('goTo', '/sdc-dummy/sdc-dummy', {text: 'SUB DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY A');
    });

    test('Navigate next level [A.1]', async () => {
        trigger('goTo', 'sdc-dummy', {text: 'SUB DUMMY A.1'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY A.1');
    });

    test('Navigate next level [A.2]', async () => {
        trigger('goTo', './sdc-dummy', {text: 'SUB DUMMY A.2'});
        await new Promise(resolve => setTimeout(resolve, 300));
        let idx = controller._origin_target.length - 1
        expect(controller.find(`.${idx}_sdc_sub_detail_container.active`).text().trim()).toBe('SUB DUMMY A.2');
    });

    test('Navigate next level [B]', async () => {
        trigger('goTo', ['/', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY B');
    });

    test('Navigate next level [C]', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY C'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY C');
    });

    test('Navigate back level [A]', async () => {
        await new Promise(resolve => setTimeout(resolve, 300));
        trigger('goTo', ['/', 'sdc-dummy'], {text: 'DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 300));
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 300));
        trigger('goTo', ['..']);
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY A');
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('');
    });

    test('Navigate back level [B]', async () => {
        trigger('goTo', ['/', 'sdc-dummy'], {text: 'DUMMY B'});
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        trigger('goTo', ['..']);
        await new Promise(resolve => setTimeout(resolve, 1000));

        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY B');
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('');
    });

    test('Navigate deep level', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.sdc_sub_detail_container.active').data('nav-idx')).toBe(3);
        expect(controller.find('.sdc_sub_detail_container.empty').length).toBe(4);
    });

    test('Navigate deep level & back [A]', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY A'});
        trigger('goTo', ['..', '..']);
        await new Promise(resolve => setTimeout(resolve, 300));
        expect(controller.find('.sdc_sub_detail_container.active').data('nav-idx')).toBe(1);
        expect(controller.find('.sdc_sub_detail_container.empty').length).toBe(2);
    });

    test('Navigate deep level & back [B]', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 300));
        let state = controller._handleUrl('..~..~sdc-dummy');
        controller._origin_target = state.path;
        let viewObj = controller._getSubViewObj(state.args);
        expect(viewObj.isBack).toBe(true);
    });

    test('Navigate deep level & false back', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 300));
        let state = controller._handleUrl('..~..~sdc-dummy~&text=DUMMY XXX');
        controller._origin_target = state.path;
        let viewObj = controller._getSubViewObj(state.args);
        expect(viewObj.isBack).toBe(false);
    });

});

describe('Sdc details', () => {
    let controller;

     beforeEach(async () => {
         controller = (await test_utils.controllerFromTestHtml(<div>
            <sdc-detail-view data-model="Book" data-pk={1}></sdc-detail-view>
         </div>))[0];


        await controller.noOpenModelRequests();
        // Wait for DOM to be updated
        await new Promise(resolve => setTimeout(resolve, 300))
     });

     test('test_details', () => {
        expect(controller.$container.html()).toBe("<div class=\"detail-container\"><div class=\"container-fluid\">\n\n<h3>Book object (1)</h3></div></div>");
     });
});

describe('SdcDummy', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-dummy',
            {text: 'Test 1'},
            '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-dummy');
        expect($div.length).toBeGreaterThan(0);
        expect($div.text()).toBe("\n    Test 1\n    \n        Controller Loaded\n    \n");
    });

});

describe('SdcSearchSelect', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-search-select',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-search-select');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('SdcAiAssistant', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-ai-assistant',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-ai-assistant');
        expect($div.length).toBeGreaterThan(0);
    });

    test('Enter in the prompt sends it, Shift+Enter does not', () => {
        const sent = [];
        if (controller._socket instanceof WebSocket) {
            controller._socket.onmessage = null;
            controller._socket.onclose = null;
            controller._socket.close();
        }
        controller._socket = {readyState: WebSocket.OPEN, send: (msg) => sent.push(JSON.parse(msg))};
        controller._busy = false;
        const textarea = controller.find('.ai-prompt-form textarea')[0];
        const key = (shiftKey) => {
            const ev = new KeyboardEvent('keydown', {key: 'Enter', shiftKey, bubbles: true, cancelable: true});
            textarea.dispatchEvent(ev);
            return ev;
        };
        textarea.value = 'first line';
        expect(key(true).defaultPrevented).toBe(false);
        expect(sent).toEqual([]);
        const ev = key(false);
        expect(sent.map((m) => m.prompt)).toEqual(['first line']);
        expect(ev.defaultPrevented).toBe(true);
        expect(textarea.value).toBe('');
        controller._setBusy(false);
        controller._socket = null;
    });

    test('Esc stops the running answer and collapses the panel', async () => {
        const sent = [];
        if (controller._socket instanceof WebSocket) {
            controller._socket.onmessage = null;
            controller._socket.onclose = null;
            controller._socket.close();
        }
        controller._socket = {readyState: WebSocket.OPEN, send: (msg) => sent.push(JSON.parse(msg))};
        const $container = controller.find('.ai-conversation-container');
        const esc = (target = document.body) => {
            const ev = new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true});
            target.dispatchEvent(ev);
            return ev;
        };
        // Collapsed: Esc belongs to the page
        controller._setCollapsed(true);
        expect(esc().defaultPrevented).toBe(false);
        // Open and answering: stopped, late messages of the answer are ignored, the panel collapses
        controller._setCollapsed(false);
        controller._busy = true;
        const id = controller._requestId;
        expect(esc(controller.find('.ai-prompt-input')[0]).defaultPrevented).toBe(true);
        expect(sent).toEqual([{event: 'stop', id}]);
        expect(controller._busy).toBe(false);
        expect(controller._requestId).not.toBe(id);
        expect($container.hasClass('collapsed')).toBe(true);
        expect(controller.find('.ai-messages .ai-message').last().text()).toBe('Stopped.');
        await controller._onMessage({type: 'ai_delta', id, text: 'late'});
        expect(controller.find('.ai-messages').text()).not.toContain('late');
        // Open and idle: only collapses; with a modal of the page open, Esc closes the modal instead
        controller._setCollapsed(false);
        esc();
        expect($container.hasClass('collapsed')).toBe(true);
        expect(sent.length).toBe(1);
        controller._setCollapsed(false);
        const $modal = $('<div class="modal show"></div>').appendTo('body');
        expect(esc().defaultPrevented).toBe(false);
        expect($container.hasClass('collapsed')).toBe(false);
        $modal.remove();
        controller._setCollapsed(true);
        controller.find('.ai-messages').empty();
        controller._socket = null;
    });

    describe('window', () => {
        const pointer = (el, type, x, y) => el.dispatchEvent(new MouseEvent(type, {bubbles: true, button: 0, clientX: x, clientY: y}));
        let $container, header;

        beforeEach(() => {
            window.localStorage.removeItem('sdc_ai_window');
            controller._saveGeometry(null);
            controller._setCollapsed(false);
            $container = controller.find('.ai-conversation-container');
            header = controller.find('.ai-header')[0];
            // jsdom has no layout: the docked window is 360 x 700 at the right edge of the 1024 x 768 viewport
            $container[0].getBoundingClientRect = () => ({left: 664, top: 0, width: 360, height: 700});
        });

        test('dragging the header moves the window and keeps it', () => {
            pointer(header, 'pointerdown', 700, 10);
            pointer(document, 'pointermove', 500, 60);
            expect($container.hasClass('dragging')).toBe(true);
            pointer(document, 'pointerup', 500, 60);
            expect($container.hasClass('floating') && !$container.hasClass('dragging')).toBe(true);
            expect($container[0].style.left).toBe('464px');
            expect($container[0].style.top).toBe('50px');
            expect(JSON.parse(window.localStorage.getItem('sdc_ai_window'))).toEqual({left: 464, top: 50, width: 360, height: 700});
        });

        test('resizing keeps the opposite edge and the minimum size, the window stays in the viewport', () => {
            pointer(controller.find('.ai-resize-w')[0], 'pointerdown', 664, 300);
            pointer(document, 'pointermove', 464, 300);
            pointer(document, 'pointerup', 464, 300);
            expect(controller._geometry).toEqual({left: 464, top: 0, width: 560, height: 700});
            pointer(controller.find('.ai-resize-w')[0], 'pointerdown', 464, 300);
            $container[0].getBoundingClientRect = () => ({left: 464, top: 0, width: 560, height: 700});
            pointer(document, 'pointermove', 1000, 300);
            pointer(document, 'pointerup', 1000, 300);
            expect(controller._geometry.width).toBe(280);
            expect(controller._geometry.left).toBe(1024 - 280);
            expect(controller._clampGeometry({left: 900, top: -20, width: 400, height: 2000}))
                .toEqual({left: 624, top: 0, width: 400, height: 768});
        });

        test('collapsing docks the tab, expanding restores the window; a double click docks it', () => {
            controller._saveGeometry({left: 10, top: 10, width: 300, height: 300});
            controller._setCollapsed(true);
            expect($container.hasClass('floating')).toBe(false);
            expect($container[0].style.left).toBe('');
            pointer(header, 'pointerdown', 20, 20);
            expect($container.hasClass('dragging')).toBe(false);  // the collapsed tab is not movable
            controller._setCollapsed(false);
            expect($container[0].style.left).toBe('10px');
            header.dispatchEvent(new MouseEvent('dblclick', {bubbles: true}));
            expect($container.hasClass('floating')).toBe(false);
            expect(window.localStorage.getItem('sdc_ai_window')).toBe(null);
        });
    });

    describe('page actions', () => {
        let $page, events, getClientRects;

        beforeEach(() => {
            // jsdom has no layout: elements count as visible unless they have the class "invisible"
            getClientRects = Element.prototype.getClientRects;
            Element.prototype.getClientRects = function () {
                return this.closest('.invisible') ? [] : [{}];
            };
            $page = $(`<div class="ai-test-page">
                <h2>Edit author</h2><p class="invisible">secret note</p><script>var x = 1;</script>
                <form SdcModelName="Author" SdcModelPK="3" class="foo" data-x="1">
                    <label for="ai-name">Name</label><input id="ai-name" name="name" value="Jo">
                    <input name="age" type="number" value="3">
                    <input name="active" type="checkbox">
                    <select name="city"><option value="1">Berlin</option><option value="2">Paris</option></select>
                    <input name="password" type="password" value="pw-123">
                    <input name="csrfmiddlewaretoken" type="hidden" value="tok-456">
                    <button type="submit">Save</button>
                </form>
                <form><input name="q"></form>
            </div>`).appendTo('body');
            events = [];
            $page.find('input, select').each(function () {
                this.addEventListener('input', () => events.push(`input:${this.name}`));
                this.addEventListener('change', () => events.push(`change:${this.name}`));
            });
        });

        afterEach(() => {
            Element.prototype.getClientRects = getClientRects;
            $page.remove();
        });

        test('read_page describes the page without secrets', () => {
            const page = controller._readPage({mode: 'html'});
            const forms = page.forms.filter((f) => f.fields.some((x) => ['name', 'q'].includes(x.name)));
            expect(forms.map((f) => f.sdc_model_name)).toEqual(['Author', null]);
            const author = forms[0];
            expect(author.sdc_model_pk).toBe(3);
            const fields = Object.fromEntries(author.fields.map((f) => [f.name, f]));
            expect(fields.name).toMatchObject({type: 'text', label: 'Name', value: 'Jo'});
            expect(fields.active.value).toBe(false);
            expect(fields.city.options).toEqual([{value: '1', label: 'Berlin'}, {value: '2', label: 'Paris'}]);
            expect(fields.password.value).toBeUndefined();
            expect(fields.csrfmiddlewaretoken.value).toBeUndefined();
            expect(page.html).toContain('<h2>Edit author</h2>');
            expect(page.html).toContain('sdcmodelname="Author"');
            for (const hidden of ['secret note', 'var x', 'pw-123', 'tok-456', 'class="foo"', 'data-x']) {
                expect(page.html).not.toContain(hidden);
            }
        });

        test('fill_form enters values like the user: input per field, change at the end', () => {
            const id = controller._readPage().forms.find((f) => f.sdc_model_name === 'Author').id;
            const result = controller._fillForm({form: id, values: {
                name: 'Jane', active: true, city: 'Paris', password: 'x', csrfmiddlewaretoken: 'y', nope: 1,
            }});
            expect(result.set).toEqual({name: 'Jane', active: true, city: '2'});
            expect(Object.keys(result.errors).sort()).toEqual(['csrfmiddlewaretoken', 'nope', 'password']);
            expect($page.find('[name=password]').val()).toBe('pw-123');
            // change after all values are set: auto-saving edit forms save, other listeners react
            expect(events).toEqual(['input:name', 'input:active', 'input:city', 'change:name', 'change:active',
                'change:city']);
            expect(result.note).toContain('saved the changed values at once');
        });

        test('fill_form fires change in other forms', () => {
            const id = controller._readPage().forms.find((f) => f.fields.some((x) => x.name === 'q')).id;
            controller._fillForm({form: id, values: {q: 'books'}});
            expect(events).toEqual(['input:q', 'change:q']);
            expect(() => controller._fillForm({form: 99999, values: {}})).toThrow('There is no form 99999');
        });

        test('forms of inactive views are left out', () => {
            // The navigator keeps the previous copy of a reopened view hidden in the page
            const $views = $(`<div>
                <div class="sdc_sub_detail_container"><form SdcModelName="Book" SdcModelPK="-1">
                    <input name="title" value="old"></form></div>
                <div class="sdc_sub_detail_container active"><form SdcModelName="Book" SdcModelPK="-1">
                    <input name="title" value=""></form></div>
            </div>`).appendTo($page);
            const books = controller._readPage().forms.filter((f) => f.sdc_model_name === 'Book');
            expect(books.length).toBe(1);
            controller._fillForm({form: books[0].id, values: {title: 'New'}});
            expect($views.find('.active [name=title]').val()).toBe('New');
            expect($views.find(':not(.active) > form [name=title]').val()).toBe('old');
        });

        test('no new prompt while a request runs; stale actions are not run', async () => {
            const sent = [];
            controller._socket = {readyState: WebSocket.OPEN, send: (msg) => sent.push(JSON.parse(msg))};
            const $textarea = controller.find('.ai-prompt-form textarea');
            $textarea.val('first');
            controller._sendPrompt();
            $textarea.val('second');
            controller._sendPrompt();
            expect(sent.map((m) => m.prompt)).toEqual(['first']);
            expect(controller.find('.ai-prompt-form [type="submit"]').prop('disabled')).toBe(true);
            expect($textarea.val()).toBe('second');  // kept for later
            const id = controller._requestId;
            await controller._onMessage({type: 'error', id, msg: 'x'});
            expect(controller._busy).toBe(false);

            // Actions of a request that is no longer the current one stop before the next action
            const read = [];
            controller._actions.read_page = () => {
                read.push(1);
                controller._requestId += 1;
                return {};
            };
            const actions = [{tool_use_id: 'a', name: 'read_page', input: {}}, {tool_use_id: 'b', name: 'read_page', input: {}}];
            expect(await controller._runActions(actions, controller._requestId)).toBeNull();
            expect(read.length).toBe(1);
            controller._socket = null;
        });

        test('error views of active views are found, also with the navigator\'s suffixed tag', () => {
            const $views = $(`<div>
                <div class="sdc_sub_detail_container"><sdc-error data-code="500"></sdc-error></div>
                <div class="sdc_sub_detail_container active">
                    <sdc-error_sdc-navigation-client data-code="404"></sdc-error_sdc-navigation-client></div>
                <div><sdc-error data-code="403"></sdc-error></div>
            </div>`).appendTo($page);
            controller.find('.ai-messages').append('<sdc-error data-code="401"></sdc-error>');
            expect(controller._errorViews()).toEqual(['404', '403']);
            $views.remove();
            controller.find('.ai-messages sdc-error').remove();
            expect(controller._errorViews()).toEqual([]);
        });

        test('navigate fails when the opened view shows an error page', async () => {
            const $error = $('<sdc-error data-code="404"></sdc-error>').appendTo($page);
            await expect(controller._navigate({path: '.'})).rejects.toThrow(
                /^Navigation to \. failed: the view shows an error page \(404: this view does not exist\)\. Now at /);
            $error.attr('data-code', '403');
            await expect(controller._navigate({path: '.'})).rejects.toThrow('403: the user may not open this view');
            $error.remove();
            await expect(controller._navigate({path: '.'})).resolves.toMatch(/^Now at /);
            // The model gets the failure as an error result
            controller._socket = {readyState: WebSocket.OPEN, send: () => null};
            $page.append('<sdc-error data-code="404"></sdc-error>');
            const [result] = await controller._runActions([{tool_use_id: 'n', name: 'navigate', input: {path: '.'}}],
                controller._requestId);
            expect(result).toMatchObject({tool_use_id: 'n', is_error: true});
            expect(result.content).toContain('404: this view does not exist');
            $page.find('sdc-error').remove();
            controller._socket = null;
        });

        test('fields outside a form are one form per controller', () => {
            const $loose = $(`<div>
                <ai-loose-view><label for="ai-user">User</label><input id="ai-user" name="username">
                    <div><select name="kind"><option value="a">A</option><option value="b">B</option></select></div>
                    <input name="secret" type="password"></ai-loose-view>
                <ai-other-view><textarea name="note"></textarea></ai-other-view>
                <div class="sdc_sub_detail_container"><ai-old-view><input name="old"></ai-old-view></div>
            </div>`).appendTo($page);
            $loose.find('input, select, textarea').each(function () {
                this.addEventListener('input', () => events.push(`input:${this.name}`));
                this.addEventListener('change', () => events.push(`change:${this.name}`));
            });
            const loose = controller._readPage().forms.filter((f) => f.form_element === false);
            expect(loose.map((f) => [f.controller, f.fields.map((x) => x.name)])).toEqual([
                ['ai-loose-view', ['username', 'kind', 'secret']], ['ai-other-view', ['note']]]);
            expect(loose[0]).toMatchObject({sdc_model_name: null, sdc_model_pk: null, visible: true});
            expect(loose[0].fields[0].label).toBe('User');

            const result = controller._fillForm({form: loose[0].id, values: {username: 'jane', kind: 'B', secret: 'x'}});
            expect(result.set).toEqual({username: 'jane', kind: 'b'});
            expect(Object.keys(result.errors)).toEqual(['secret']);
            expect(result.note).toContain('Nothing was submitted');
            expect($loose.find('[name=username]').val()).toBe('jane');
            expect(events).toEqual(['input:username', 'input:kind', 'change:username', 'change:kind']);
            // Real forms come before the loose fields; ids stay the same on the next read
            const forms = controller._readPage().forms;
            expect(forms.findIndex((f) => f.sdc_model_name === 'Author'))
                .toBeLessThan(forms.findIndex((f) => f.id === loose[0].id));
            $loose.remove();
        });

        test('a hanging action returns an error result instead of blocking the answer', async () => {
            controller._socket = {readyState: WebSocket.OPEN, send: () => null};
            controller._actionTimeoutMs = 50;
            const original = controller._actions.model_load;
            controller._actions.model_load = () => new Promise(() => null);  // never settles
            const [result, next] = await controller._runActions([
                {tool_use_id: 'h', name: 'model_load', input: {model: 'Author'}},
                {tool_use_id: 'r', name: 'read_page', input: {}},
            ], controller._requestId);
            expect(result).toMatchObject({tool_use_id: 'h', is_error: true});
            expect(result.content).toContain('model_load did not finish within 0.05s');
            expect(next).toMatchObject({tool_use_id: 'r', is_error: false});
            controller._actions.model_load = original;
            delete controller._actionTimeoutMs;
            controller._socket = null;
        });

        test('the outline shows text with element markers, no HTML, and no secrets', () => {
            const page = controller._readPage();
            expect(page.html).toBeUndefined();
            expect(page.text).toContain('## Edit author');
            const save = page.elements.find((e) => e.text === 'Save');
            expect(page.text).toContain(`[#${save.id} Save]`);
            for (const hidden of ['secret note', 'var x', 'pw-123', 'tok-456', 'Jo']) {
                expect(page.text).not.toContain(hidden);
            }
            // A scope limits the outline; an unknown scope is an error
            const author = page.forms.find((f) => f.sdc_model_name === 'Author');
            const scoped = controller._readPage({scope: author.id});
            expect(scoped.forms.map((f) => f.id)).toEqual([author.id]);
            expect(scoped.text).not.toContain('Edit author');
            expect(controller._readPage({scope: author.id, mode: 'html'}).html).toMatch(/^<form /);
            expect(() => controller._readPage({scope: 99999})).toThrow('no element, form or list 99999');
            expect(() => controller._readPage({mode: 'xml'})).toThrow('mode must be');
        });

        test('long lists and paged lists are summarised with their search bar', () => {
            const rows = Array.from({length: 30}, (_, i) =>
                `<tr><td>Writer ${i + 1}</td><td><a class="navigation-links" href="/~sdc-detail-view~&pk=${i + 1}">Detail</a></td></tr>`).join('');
            const $list = $(`<div class="_sdc_controller_"><sdc-search-view>
                    <div class="inner-form search-form"><input name="search" class="timer-change"></div>
                    <div class="page-number-control"><button class="page-number-control-btn page-number-control-btn-prev">Prev</button>
                    <span class="range-span">1 - 30</span><span class="total-amount-span"> / 306</span>
                    <button class="page-number-control-btn page-number-control-btn-next">Next</button></div>
                </sdc-search-view><table><tbody>${rows}</tbody></table>
                <ul><li>a</li><li>b</li></ul></div>`).appendTo($page);
            const page = controller._readPage();
            const [list] = page.lists;
            expect(page.lists.length).toBe(1);  // the short <ul> stays text
            expect(list).toMatchObject({kind: 'table', rows_in_page: 30, rows_shown: [1, 20]});
            expect(list.rows[0].text).toBe('Writer 1 | Detail');
            expect(list.rows[0].elements[0]).toMatchObject({text: 'Detail'});
            expect(list.more_rows).toContain(`scope: ${list.id}`);
            expect(list.search).toMatchObject({range: '1 - 30', total: 306, next_disabled: false});
            const search = page.forms.find((f) => f.fields.some((x) => x.name === 'search'));
            expect(list.search.form).toBe(search.id);
            // Row elements are not repeated in elements; the text only references the list
            expect(page.elements.some((e) => e.text === 'Detail')).toBe(false);
            expect(page.text).toContain(`[list #${list.id}: 30 rows, see lists]`);
            expect(page.text).not.toContain('Writer 7');
            expect(page.text).toContain('- b'.slice(2));
            // More rows of the list
            const more = controller._readPage({scope: list.id, rows: [21, 30]});
            expect(more.lists[0].rows.map((r) => r.n)).toEqual([21, 22, 23, 24, 25, 26, 27, 28, 29, 30]);
            expect(more.lists[0].rows[0].text).toBe('Writer 21 | Detail');
            // Next is a stable element id
            expect(controller._pageElements().find((el) => controller._ids.get(el) === list.search.next).textContent)
                .toBe('Next');
            $list.remove();
        });

        test('Restore in the chat sets the previous values back and fires the events again', () => {
            const id = controller._readPage().forms.find((f) => f.sdc_model_name === 'Author').id;
            controller._fillForm({form: id, values: {name: 'Jane', active: true, city: 'Paris'}});
            const $msg = controller.find('.ai-restore').last();
            expect($msg.text()).toContain('Changed name, active, city in Author.');
            events.length = 0;
            $msg.find('.ai-restore-button').trigger('click');
            expect($page.find('[name=name]').val()).toBe('Jo');
            expect($page.find('[name=active]').prop('checked')).toBe(false);
            expect($page.find('[name=city]').val()).toBe('1');
            expect(events).toEqual(['input:name', 'input:active', 'input:city', 'change:name', 'change:active',
                'change:city']);
            expect($msg.find('.ai-restore-button').length).toBe(0);
            expect($msg.text()).toContain('Restored the previous values.');
            // A form that is gone cannot be restored
            controller._fillForm({form: id, values: {name: 'Again'}});
            const $second = controller.find('.ai-restore').last();
            $page.find('form').first().remove();
            $second.find('.ai-restore-button').trigger('click');
            expect($second.text()).toContain('no longer on the page');
            controller.find('.ai-messages').empty();
        });

        test('fill_form warns about invisible forms', () => {
            const $hidden = $('<div class="invisible"><form><input name="z"></form></div>').appendTo($page);
            const id = controller._readPage().forms.find((f) => f.fields.some((x) => x.name === 'z')).id;
            expect(controller._fillForm({form: id, values: {z: '1'}}).warning).toContain('not visible');
            $hidden.remove();
        });

        describe('navigate path check', () => {
            let nav, savedNav;

            beforeEach(() => {
                // The real navigator resolves the paths; goTo only records them
                savedNav = window.sdcNav;
                nav = new SdcNavigatorController();
                nav._history_path = ['dashboard'];
                nav.opened = [];
                nav.goTo = (path) => nav.opened.push(path);
                window.sdcNav = nav;
                // The real connection to the test server would replace _config with the server's ai_config
                if (controller._socket instanceof WebSocket) {
                    controller._socket.onmessage = null;
                    controller._socket.onclose = null;
                    controller._socket.close();
                }
                controller._socket = null;
                controller._config = {view_paths: {
                    settings: ['/~dashboard~settings'],
                    profile: ['/~dashboard~profile', '/~admin~profile'],
                }};
            });

            afterEach(() => {
                window.sdcNav = savedNav;
                controller._config = null;
            });

            test('crawled, relative and unknown paths are opened unchanged', () => {
                expect(controller._checkNavigationPath('/~dashboard~settings~&pk=3')).toEqual(
                    {path: '/~dashboard~settings~&pk=3'});
                expect(controller._checkNavigationPath('.~settings')).toEqual({path: '.~settings'});
                expect(controller._checkNavigationPath('/~other-view')).toEqual({path: '/~other-view'});
                controller._config = {};
                expect(controller._checkNavigationPath('/~settings')).toEqual({path: '/~settings'});
            });

            test('a path without the views in front is corrected, arguments with a depth are shifted', () => {
                const checked = controller._checkNavigationPath('/~settings~&pk=3&1.tab=2');
                expect(checked.path).toBe('/~dashboard~settings~&pk=3&2.tab=2');
                expect(checked.note).toContain('settings only works at /~dashboard~settings');
                expect(controller._checkNavigationPath('~settings').path).toBe('/~dashboard~settings');
            });

            test('an ambiguous or wrong path is refused with the crawled paths', () => {
                expect(() => controller._checkNavigationPath('/~profile')).toThrow(
                    'Navigation to /~profile refused: it opens profile at /~profile, but profile only works at '
                    + '/~dashboard~profile, /~admin~profile.');
                expect(() => controller._checkNavigationPath('/~other~settings')).toThrow('only works at /~dashboard~settings');
            });

            test('navigate opens the corrected path and tells the model', async () => {
                const result = await controller._navigate({path: '/~settings'});
                expect(nav.opened).toEqual(['/~dashboard~settings']);
                expect(result).toMatch(/^Now at .*\. \/~settings left out the views in front of settings/);
                await expect(controller._navigate({path: '/~profile'})).rejects.toThrow('refused');
                expect(nav.opened).toEqual(['/~dashboard~settings']);
            });
        });

        describe('buttons and links', () => {
            let $buttons, clicks, nav, savedNav;
            const element = (text) => controller._readPage().elements.find((e) => e.text === text);

            beforeEach(() => {
                // A navigator stub: the assistant resolves and opens SDC links with its functions
                savedNav = window.sdcNav;
                nav = {
                    _non_controller_path_prefix: '/', _is_processing: false, opened: [],
                    _prepareUrl: (href) => href.replace(/^\.\.~/, '~main-view~'),
                    _handleUrl(href) {
                        this._non_controller_path_prefix = 'changed';
                        return {href: `/${href}`, path: href.split('~').filter(Boolean), args: {}};
                    },
                    goTo(path) {
                        this.opened.push(path);
                    },
                };
                window.sdcNav = nav;
                $buttons = $(`<ai-button-view>
                    <button class="ai-next" type="button" sdc_click="this.event_.ai-next nextPage">Next</button>
                    <button class="ai-open-modal" type="button" data-bs-toggle="modal">Remove</button>
                    <button class="ai-delete" type="button" sdc_click="removeInstance">Remove Jane</button>
                    <button class="ai-off" type="button" disabled>Off</button>
                    <a class="navigation-links" href="..~book-list">Books</a>
                    <a href="https://example.com/help">Help</a>
                    <a href="#top">Top</a>
                    <form><input name="search" class="timer-change"><button>Find</button></form>
                    <button class="invisible">Hidden</button>
                </ai-button-view>`).appendTo($page);
                clicks = [];
                $buttons.find('button').each(function () {
                    this.addEventListener('click', (ev) => {
                        ev.preventDefault();
                        clicks.push(this.textContent);
                    });
                });
                // The real connection to the test server would replace _config with the server's ai_config
                if (controller._socket instanceof WebSocket) {
                    controller._socket.onmessage = null;
                    controller._socket.onclose = null;
                    controller._socket.close();
                }
                controller._socket = {readyState: WebSocket.OPEN, send: () => null};
                // jsdom: no server answers a click, so the click does not wait for an update to start
                controller._clickUpdateStartMs = 0;
            });

            afterEach(() => {
                window.sdcNav = savedNav;
                controller._config = null;
                controller._socket = null;
                controller.find('.ai-messages').empty();
                $buttons.remove();
            });

            test('read_page lists the visible buttons and links with the navigator\'s link targets', () => {
                const page = controller._readPage();
                expect(element('Next')).toMatchObject({kind: 'button', controller: 'ai-button-view',
                    handlers: ['nextPage']});
                expect(element('Next').needs_confirmation).toBeUndefined();
                expect(element('Remove Jane').needs_confirmation).toBe(true);
                // Only opens a modal (the real "Remove …" button inside it asks)
                expect(element('Remove')).toMatchObject({toggles: 'modal'});
                expect(element('Remove').needs_confirmation).toBeUndefined();
                expect(element('Off')).toMatchObject({clickable: false, reason: 'the element is disabled'});
                expect(element('Books')).toMatchObject({kind: 'link', href: '/~main-view~book-list'});
                expect(element('Help')).toMatchObject({external: true, clickable: false});
                expect(element('Find')).toMatchObject({clickable: false});
                expect(element('Find').reason).toContain('submits a form');
                expect(page.elements.some((e) => e.text === 'Hidden')).toBe(false);
                // Resolving a link does not change the navigator
                expect(nav._non_controller_path_prefix).toBe('/');
                expect(controller._readPage({mode: 'html'}).html).toContain(`data-ai-element="${element('Next').id}"`);
                expect(page.text).toContain(`[#${element('Next').id} Next]`);
                expect(document.querySelector('[data-ai-element]')).toBeNull();
                // A search bar updates its view on change
                const search = page.forms.find((f) => f.fields.some((x) => x.name === 'search'));
                expect(search.updates_on_change).toBe(true);
                expect(controller._fillForm({form: search.id, values: {search: 'jane'}}).note)
                    .toContain('updates by itself');
            });

            test('click runs a button\'s handler and opens SDC links with the navigator', async () => {
                const result = await controller._click({element: element('Next').id});
                expect(clicks).toEqual(['Next']);
                expect(result).toMatchObject({clicked: 'Next', navigated: false});
                await controller._click({element: element('Books').id});
                expect(nav.opened).toEqual(['..~book-list']);
                await expect(controller._click({element: element('Find').id})).rejects.toThrow('submits a form');
                await expect(controller._click({element: element('Help').id})).rejects.toThrow('leaves the app');
                await expect(controller._click({element: 99999})).rejects.toThrow('There is no element 99999');
                expect(clicks).toEqual(['Next']);
            });

            test('a risky click waits for the user\'s permission', async () => {
                const action = {tool_use_id: 'c', name: 'click', input: {element: element('Remove Jane').id}};
                let running = controller._runActions([action], controller._requestId);
                await new Promise((resolve) => setTimeout(resolve, 10));
                expect(controller.find('.ai-confirm').text()).toContain('wants to click "Remove Jane"');
                controller.find('.ai-confirm-deny').trigger('click');
                let [result] = await running;
                expect(result.is_error).toBe(true);
                expect(result.content).toContain('did not allow');
                expect(clicks).toEqual([]);

                running = controller._runActions([action], controller._requestId);
                await new Promise((resolve) => setTimeout(resolve, 10));
                controller.find('.ai-confirm-allow').last().trigger('click');
                [result] = await running;
                expect(result).toMatchObject({is_error: false, content: {clicked: 'Remove Jane'}});
                expect(clicks).toEqual(['Remove Jane']);
            });

            test('ids stay with their element; a changed or removed element is refused', async () => {
                const next = element('Next').id;
                // A new element before "Next" does not change its id (an index would have moved)
                $buttons.prepend('<button type="button" class="ai-new">New</button>');
                expect(element('Next').id).toBe(next);
                expect(element('New').id).not.toBe(next);
                await expect(controller._click({element: next, text: 'next'})).resolves.toMatchObject({clicked: 'Next'});
                $buttons.find('.ai-next').text('Back');
                await expect(controller._click({element: next, text: 'Next'})).rejects.toThrow('is now "Back"');
                $buttons.find('.ai-next').remove();
                await expect(controller._click({element: next})).rejects.toThrow('no longer on the page');
                // Forms keep their ids too
                const search = controller._readPage().forms.find((f) => f.fields.some((x) => x.name === 'search'));
                $buttons.find('form').before('<form><input name="other"></form>');
                expect(controller._readPage().forms.find((f) => f.fields.some((x) => x.name === 'search')).id)
                    .toBe(search.id);
            });

            test('with page_in_results, actions return the page afterwards', async () => {
                controller._config = {page_in_results: true};
                const result = await controller._actions.click.call(controller, {element: element('Next').id});
                expect(result).toMatchObject({clicked: 'Next'});
                expect(result.note).toBeUndefined();
                expect(result.page.elements.some((e) => e.text === 'Next')).toBe(true);
                // A string result (navigate) becomes {result, page}
                const navigated = await controller._withPage('Now at /~x');
                expect(navigated).toMatchObject({result: 'Now at /~x'});
                expect(navigated.page.url).toBe(window.location.pathname);
                controller._config = {page_in_results: false};
                expect(await controller._withPage('Now at /~x')).toBe('Now at /~x');
            });

            test('fill_form of a search bar waits until the view is ready and its update arrived', async () => {
                const search = controller._readPage().forms.find((f) => f.fields.some((x) => x.name === 'search'));
                const $form = $buttons.find('form');
                // An sdc-update-on-change controller that ignores changes right after rendering
                const owner = {_isNotReady: true};
                $form.data('_controller_', owner);
                setTimeout(() => {
                    owner._isNotReady = false;
                }, 150);
                const seen = [];
                $form.find('[name=search]')[0].addEventListener('change', () => {
                    seen.push(owner._isNotReady ? 'too early' : 'ready');
                    // The filtered list arrives later
                    setTimeout(() => $buttons.append('<p class="ai-result">Jane</p>'), 100);
                });
                controller._updateStartMs = 1000;
                controller._config = {page_in_results: true};
                const result = await controller._actions.fill_form.call(controller, {form: search.id, values: {search: 'jane'}});
                expect(seen).toEqual(['ready']);
                expect(result.set).toEqual({search: 'jane'});
                expect(result.page.text).toContain('Jane');
                delete controller._updateStartMs;
            });

            test('an unanswered question ends with its request', async () => {
                const action = {tool_use_id: 'c', name: 'click', input: {element: element('Remove Jane').id}};
                const running = controller._runActions([action], controller._requestId);
                await new Promise((resolve) => setTimeout(resolve, 10));
                controller._requestId += 1;
                expect(await running).toBeNull();
                expect(clicks).toEqual([]);
            });
        });
    });

});

describe('AI assistant Markdown', () => {
    const render = (md) => {
        const div = document.createElement('div');
        div.append(renderMarkdown(md));
        return div;
    };
    const html = (md) => render(md).innerHTML;

    test('blocks', () => {
        expect(html('# Title\nText line\nnext line')).toBe(
            '<div class="ai-md-heading ai-md-h1">Title</div><p>Text line<br>next line</p>');
        expect(html('- a\n- b\n  - b1\n  - b2\n- c')).toBe(
            '<ul><li>a</li><li>b<ul><li>b1</li><li>b2</li></ul></li><li>c</li></ul>');
        expect(html('3. three\n4. four')).toBe('<ol start="3"><li>three</li><li>four</li></ol>');
        expect(html('```js\nconst a = 1 < 2;\n```\nafter')).toBe(
            '<pre class="ai-md-code"><code data-language="js">const a = 1 &lt; 2;</code></pre><p>after</p>');
        expect(html('> quoted **bold**\n> more')).toBe('<blockquote><p>quoted <strong>bold</strong><br>more</p></blockquote>');
        expect(html('| Name | Age |\n|:--|--:|\n| Jane | 40 |')).toBe(
            '<div class="ai-md-table"><table><thead><tr><th style="text-align: left;">Name</th>' +
            '<th style="text-align: right;">Age</th></tr></thead><tbody><tr><td style="text-align: left;">Jane</td>' +
            '<td style="text-align: right;">40</td></tr></tbody></table></div>');
        expect(html('a\n\n* * *\n\nb')).toBe('<p>a</p><hr><p>b</p>');
    });

    test('inline', () => {
        expect(html('`x_y` **b** *i* _i2_ ~~s~~ sdc_user_nav_btn')).toBe(
            '<p><code>x_y</code> <strong>b</strong> <em>i</em> <em>i2</em> <del>s</del> sdc_user_nav_btn</p>');
        const div = render('See [the docs](https://simpledomcontrol.readthedocs.io/en/latest/), ' +
                           'https://example.com/a. and [login](/~sdc-login)');
        const [docs, bare, login] = div.querySelectorAll('a');
        expect(docs.getAttribute('href')).toBe('https://simpledomcontrol.readthedocs.io/en/latest/');
        expect(docs.target).toBe('_blank');
        expect(bare.getAttribute('href')).toBe('https://example.com/a');  // the trailing dot is not part of it
        expect(login.className).toBe('ai-md-nav');
        expect(login.target).toBe('');
    });

    test('HTML and unsafe links stay text', () => {
        const div = render('<img src=x onerror=alert(1)> <script>alert(1)</script>\n' +
                           '[click](javascript:alert(1)) [x](https://a.example/"onmouseover="alert(1))');
        expect(div.querySelector('img, script')).toBeNull();
        expect(div.textContent).toContain('<img src=x onerror=alert(1)>');
        const links = div.querySelectorAll('a');
        expect(links.length).toBe(1);
        expect([...links[0].attributes].map((a) => a.name).sort()).toEqual(['href', 'rel', 'target']);
        expect(div.textContent).toContain('[click](javascript:alert(1))');
    });

    test('incomplete syntax while streaming', () => {
        expect(html('```py\nprint(1)')).toBe('<pre class="ai-md-code"><code data-language="py">print(1)</code></pre>');
        expect(html('**bold not closed')).toBe('<p>**bold not closed</p>');
        expect(html('| a | b')).toBe('<p>| a | b</p>');
    });

    test('a streamed answer renders like the complete text', async () => {
        const controller = await test_utils.get_controller('sdc-ai-assistant', {}, '<div class="ai-messages"></div>');
        const answer = '## Books\n\n| Title | Author |\n|---|---|\n| Faust | Goethe |\n\n- **one**\n- `two`';
        controller._requestId = 7;
        for (let i = 0; i < answer.length; i += 5) {
            await controller._onMessage({type: 'ai_delta', id: 7, text: answer.slice(i, i + 5)});
        }
        await controller._onMessage({type: 'ai_answer', id: 7, text: answer});
        const bubbles = controller.find('.ai-message.assistant.ai-markdown');
        expect(bubbles.last().html()).toBe(html(answer));
        expect(controller._$answer).toBeNull();
    });
});
