/**
 * @jest-environment jsdom
 */

import {test_utils, trigger} from 'sdc_client';
import {} from "#root/src/models/src.js";
import '../src/sdc_tools/sdc_tools.organizer.js';


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
            const page = controller._readPage();
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

        test('fill_form enters values without saving SdcModel forms', () => {
            const index = controller._readPage().forms.findIndex((f) => f.sdc_model_name === 'Author');
            const result = controller._fillForm({form: index, values: {
                name: 'Jane', active: true, city: 'Paris', password: 'x', csrfmiddlewaretoken: 'y', nope: 1,
            }});
            expect(result.set).toEqual({name: 'Jane', active: true, city: '2'});
            expect(Object.keys(result.errors).sort()).toEqual(['csrfmiddlewaretoken', 'nope', 'password']);
            expect($page.find('[name=password]').val()).toBe('pw-123');
            // Only input events: the change event would make edit forms save themselves
            expect(events).toEqual(['input:name', 'input:active', 'input:city']);
        });

        test('fill_form fires change in other forms', () => {
            const index = controller._readPage().forms.findIndex((f) => f.fields.some((x) => x.name === 'q'));
            controller._fillForm({form: index, values: {q: 'books'}});
            expect(events).toEqual(['input:q', 'change:q']);
            expect(() => controller._fillForm({form: 99, values: {}})).toThrow('There is no form 99');
        });
    });

});