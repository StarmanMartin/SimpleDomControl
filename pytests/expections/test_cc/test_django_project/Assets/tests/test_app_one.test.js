/**
 * @jest-environment jsdom
 */

import {test_utils} from "sdc";

describe('TestSdcOne', () => {
    let controller, Controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        const a = await test_utils.get_controller('test_app_one',
                                       'test-sdc-one',
                                       '<div><h1>Controller Loaded</h1></div>',
                                       '<div class="">Loading</div>');
        controller = a.instance;
        Controller = a.class;
    });

    test('Load Content', async () => {
        const $div = controller.$container.find('div');
        expect($div.length).toBe(1);
    });

});

describe('TestSdcTwo', () => {
    let controller, Controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        const a = await test_utils.get_controller('test_app_one',
                                       'test-sdc-two',
                                       '<div><h1>Controller Loaded</h1></div>',
                                       '<div class="">Loading</div>');
        controller = a.instance;
        Controller = a.class;
    });

    test('Load Content', async () => {
        const $div = controller.$container.find('div');
        expect($div.length).toBe(1);
    });

});