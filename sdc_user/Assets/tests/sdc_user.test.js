/**
 * @jest-environment jsdom
 */

import {test_utils} from 'sdc_client';
import '../src/sdc_user/sdc_user.organizer.js'


describe('SdcNavigator', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc_tools', {}, '<div><h1>Controller loading...</h1></div>');
    });

    test('Load Content', async () => {
    });

});

describe('SdcUserNavBtn', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-user-nav-btn',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-user-nav-btn');
        expect($div.length).toBeGreaterThan(0);
    });

});