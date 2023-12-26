/**
 * @jest-environment jsdom
 */

import {test_utils} from 'sdc_client';
import {} from "#root/src/main_test/main_test.organizer.js";
import '#root/src/sdc_tools/sdc_tools.organizer.js'
import '#root/src/sdc_user/sdc_user.organizer.js'
import Cookies from 'js-cookie';



describe('MainView', () => {
    let controller;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);


        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('main-view',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });

    test('Flow test', async () => {
        expect(controller.flow_test).toStrictEqual(["constructor", "onInit", "onLoad", "willShow"])
    });

    test('Load content', async () => {
        const $div = $('body').find('main-view');
        expect($div.length).toBeGreaterThan(0);
        const $header = controller.find('.find-test');
        expect($header.text()).toBe("Test header");
    });

    test('Load view function content', async () => {
        expect(controller.find('.test-header').text()).toBe("test 123");
    });

    test('Load async function content', async () => {
        await new Promise((resolve)=> {
            setTimeout(resolve, 60);
        });

        expect(controller.find('.async-test-header').text()).toBe("After 50 mil.sec.");
    });

});

describe('MainView Logged out', () => {
    let controller;

    beforeAll(async () => {
        Cookies.set('sessionid', null);
        console.log('Removed session key set');


        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('main-view',
            {},
            '<div><h1>Controller Loaded</h1></div>');
    });

    test('Flow test', async () => {
        expect(controller.flow_test).toStrictEqual(["constructor", "onInit"])
    });

    test('Load Content', async () => {
        const $div = $('body').find('main-view');
        expect($div.length).toBeGreaterThan(0);
        const $header = controller.find('sdc-error');
        expect($header.data('code')).toBe(403);
    });

});

describe('AdminOnly', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('admin-only',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('admin-only');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('StaffAndAdmin', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('staff-and-admin',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('staff-and-admin');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('EditorAndStaff', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('editor-and-staff',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('editor-and-staff');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('EditorNoStaff', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('editor-no-staff',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('editor-no-staff');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('LoggedIn', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('logged-in',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('logged-in');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('Error404', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('error404',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('error404');
        expect($div.length).toBeGreaterThan(0);
    });

});