/**
 * @jest-environment jsdom
 */

import {test_utils, socketReconnect} from 'sdc_client';
import {} from "#root/src/main_test/main_test.organizer.js";
import '#root/src/sdc_tools/sdc_tools.organizer.js'
import '#root/src/sdc_user/sdc_user.organizer.js'
import Cookies from 'js-cookie';



describe('MainView server call', () => {
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

    test('Call Echo', async () => {
        const sentData = {'a': 1, 'b': true, 'c': null, 'd': 'test'};
        let res = await controller.serverCall('call_echo', sentData);
        expect(res).toStrictEqual(sentData);
    });

    test('Call no response', async () => {
        const sentData = {'a': 1, 'b': true, 'c': null, 'd': 'test'};
        let res = await controller.serverCall('call_no_response', sentData);
        expect(res).toStrictEqual(null);
    });

    test('Call no existing', async () => {
        const sentData = {'a': 1, 'b': true, 'c': null, 'd': 'test'};
        let a;
        try {
            a = await controller.serverCall('not_existing', sentData).catch((res) => {
                expect(res).toStrictEqual(null);
                throw new Error('Error');
            });
        } catch {

        }

        expect(a).toBe(undefined);
    });

});

describe('MainView server call no user', () => {
    let controller;

    beforeAll(async () => {
        Cookies.set('sessionid', null);
        console.log('Removed session key');


        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('main-view',
            {},
            '<div><h1>Controller Loaded</h1></div>');
        socketReconnect();
    });

    test('Echo call', async () => {
        const sentData = {'a': 1, 'b': true, 'c': null, 'd': 'test'};
        let a;
        try {
            a = await controller.serverCall('call_echo', sentData).catch((res) => {
                expect(res).toStrictEqual(null);
                throw new Error('Error');
            });
        } catch {
        }

        expect(a).toBe(undefined);
    });
});

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
        expect(controller.flow_test).toStrictEqual(["constructor", "onInit", "onLoad", "willShow", "onRefresh"]);
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
        await new Promise((resolve) => setTimeout(resolve, 30));
        expect(controller.find('.async-test-header').text()).toBe("After 10 mil.sec.");
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
        expect(controller.flow_test).toStrictEqual(["constructor", "onInit", "onRefresh"])
    });

    test('Load Content', async () => {
        const $div = $('body').find('main-view');
        expect($div.length).toBeGreaterThan(0);
        const $header = controller.find('sdc-error');
        expect($header.data('code')).toBe(403);
    });

});


describe('MainView events', () => {
    let controller, refreshHandler;

    beforeAll(async () => {
        const session_key = SCRIPT_OUTPUT[0];
        Cookies.set('sessionid', session_key);
        console.log('Session key set:', session_key);

        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('main-view',
            {},
            '<div><h1>Controller Loaded</h1></div>');

        const refresh = controller.onRefresh.bind(controller);
        controller.onRefresh = function () {
            refresh();
            refreshHandler && refreshHandler();
        }
    });


    beforeEach(() => {
        refreshHandler = null;
    });


    test('click function view', async () => {
        refreshHandler = () => {
            expect(controller.find('.test-header').text()).toBe("Button Pressed!! 123");
        };

        controller.find('.func_view_button').trigger('click');
        await new Promise((resolve) => setTimeout(resolve, 3000));

    });


    test('click class', async () => {
        refreshHandler = () => {
            expect(controller.find('.test-header').text()).toBe("Class click 123");
        };

        controller.find('.class_sdc_click').trigger('click');
        await new Promise((resolve) => setTimeout(resolve, 30));

    });


    test('click attr', async () => {
        refreshHandler = () => {
            expect(controller.find('.test-header').text()).toBe("attr click 123");
        };

        controller.find('.attr_sdc_click').trigger('click');
        await new Promise((resolve) => setTimeout(resolve, 30));

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

describe('TestItem', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('test-item',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('test-item');
        expect($div.length).toBeGreaterThan(0);
    });

});