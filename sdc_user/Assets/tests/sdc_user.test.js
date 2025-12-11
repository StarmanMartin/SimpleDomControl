/**
 * @jest-environment jsdom
 */

import {test_utils} from 'sdc_client';
import '../src/sdc_user/sdc_user.organizer.js'
import '#root/src/sdc_tools/sdc_tools.organizer.js'

window.gettext = (x) => x;

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

describe('User', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('user',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('user');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('SdcConfirmEmail', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-confirm-email',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-confirm-email');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('SdcUser', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-user',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-user');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('SdcChangePassword', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-change-password',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-change-password');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('SdcPasswordForgotten', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-password-forgotten',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-password-forgotten');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('SdcResetPassword', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('sdc-reset-password',
                                                  {token: 'Test'},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('sdc-reset-password');
        expect($div.length).toBeGreaterThan(0);
    });

});

describe('Register', () => {
    let controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        controller = await test_utils.get_controller('register',
                                                  {},
                                                  '<div><h1>Controller Loaded</h1></div>');
    });

    test('Load Content', async () => {
        const $div = $('body').find('register');
        expect($div.length).toBeGreaterThan(0);
    });

});