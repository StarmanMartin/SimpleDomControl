/**
 * @jest-environment jsdom
 */

import {test_utils} from "sdc";
import '../src/sdc_tools/sdc_tools.organizer.js'


describe('SdcNavigator', () => {
    let controller, Controller;

    beforeEach(async () => {
        // Create new controller instance based on the standard process.
        const a = await test_utils.get_controller('sdc_tools',
            'sdc-navigator',
            '<div><div class="main-nav-import-container"></div><div class="sdc_detail_view">Loading</div></div>',
            '<div>Loading</div>');

        controller = a.instance;
        Controller = a.class;
    });

    test('Load Content', async () => {
        const $div = controller.$container.find('div');
        expect($div.length).toBe(4);
    });

});