/**
 * @jest-environment jsdom
 */

import {test_utils} from 'sdc_client';
import {} from "#root/src/test_app_one/test_app_one.organizer.js";
import '#root/src/sdc_tools/sdc_tools.organizer.js'
import '#root/src/sdc_user/sdc_user.organizer.js'

describe('TestSdcOne', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('test-sdc-one',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('test-sdc-one');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('TestSdcTwo', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('test-sdc-two',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('test-sdc-two');
        expect($div.length).toBeGreaterThan(0);
    });

});