/**
 * @jest-environment jsdom
 */

import {test_utils, trigger} from 'sdc_client';
import '../src/sdc_tools/sdc_tools.organizer.js'


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
        for (let i = 0; i < 20; ++i) {
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
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY A');
    });

    test('Navigate same level [B]', async () => {
        trigger('goTo', ['/', 'sdc-dummy'], {text: 'DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY B');
    });

    test('Navigate same level [C]', async () => {
        trigger('goTo', ['', 'sdc-dummy'], {text: 'DUMMY C'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY C');
    });

    test('Navigate next level [A]', async () => {
        trigger('goTo', '/sdc-dummy/sdc-dummy', {text: 'SUB DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY A');
    });

    test('Navigate next level [A.1]', async () => {
        trigger('goTo', 'sdc-dummy', {text: 'SUB DUMMY A.1'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY A.1');
    });

    test('Navigate next level [A.2]', async () => {
        trigger('goTo', './sdc-dummy', {text: 'SUB DUMMY A.2'});
        await new Promise(resolve => setTimeout(resolve, 100));
        let idx = controller._origin_target.length - 1
        expect(controller.find(`.${idx}_sdc_sub_detail_container.active`).text().trim()).toBe('SUB DUMMY A.2');
    });

    test('Navigate next level [B]', async () => {
        trigger('goTo', ['/', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY B');
    });

    test('Navigate next level [C]', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY C'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('SUB DUMMY C');
    });

    test('Navigate back level [A]', async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        trigger('goTo', ['/', 'sdc-dummy'], {text: 'DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 100));
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY A'});
        await new Promise(resolve => setTimeout(resolve, 100));
        trigger('goTo', ['..']);
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY A');
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('');
    });

    test('Navigate back level [B]', async () => {
        trigger('goTo', ['/', 'sdc-dummy'], {text: 'DUMMY B'});
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        trigger('goTo', ['..']);
        await new Promise(resolve => setTimeout(resolve, 1000));
        console.log(controller);
        expect(controller.find('.0_sdc_sub_detail_container.active').text().trim()).toBe('DUMMY B');
        expect(controller.find('.1_sdc_sub_detail_container.active').text().trim()).toBe('');
    });

    test('Navigate deep level', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.sdc_sub_detail_container.active').data('nav-idx')).toBe(3);
        expect(controller.find('.sdc_sub_detail_container.empty').length).toBe(4);
    });

    test('Navigate deep level & back [A]', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY A'});
        trigger('goTo', ['..', '..']);
        await new Promise(resolve => setTimeout(resolve, 100));
        expect(controller.find('.sdc_sub_detail_container.active').data('nav-idx')).toBe(1);
        expect(controller.find('.sdc_sub_detail_container.empty').length).toBe(2);
    });

    test('Navigate deep level & back [B]', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 100));
        let state = controller._handleUrl('..~..~sdc-dummy');
        controller._origin_target = state.path;
        let viewObj = controller._getSubViewObj(state.args);
        expect(viewObj.isBack).toBe(true);
    });

    test('Navigate deep level & false back', async () => {
        trigger('goTo', ['', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy', 'sdc-dummy'], {text: 'SUB DUMMY B'});
        await new Promise(resolve => setTimeout(resolve, 100));
        let state = controller._handleUrl('..~..~sdc-dummy~&text=DUMMY XXX');
        controller._origin_target = state.path;
        let viewObj = controller._getSubViewObj(state.args);
        expect(viewObj.isBack).toBe(false);
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