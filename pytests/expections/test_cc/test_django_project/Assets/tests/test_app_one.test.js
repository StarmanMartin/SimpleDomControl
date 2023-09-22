/**
 * @jest-environment jsdom
 */

import {get_controller} from "./utils/test_utils.js";

describe('TestSdcOne', () => {
    let controller, Controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        const a = await get_controller('test_app_one',
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