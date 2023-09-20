/**
 * @jest-environment jsdom
 */

const {app} = require('./dist/sdc_main')
const sdc_view = require('./dist/sdc_view')
const {AbstractSDC} = require('./dist/AbstractSDC')
const $ = require('jquery')
window.$ = $;

class TestCtr extends AbstractSDC {
    constructor() {
        super();
        this.contentUrl = 'TestCtr'; //<test-ctr>
        this.events.unshift({});
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - afterShow  (recalled on reload)               //
    //-------------------------------------------------//
    // - onRefresh                                     //
    //-------------------------------------------------//
    // - onRemove                                      //
    //-------------------------------------------------//

    onInit() {
    }

    onLoad($html) {
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    afterShow() {
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }
}

describe('Controller', () => {

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test('Load Content', () => {
        let ctr = new TestCtr();
        ctr.$container = $('<test-ctr></test-ctr>');
        const ajaxSpy = jest.spyOn($, 'ajax');
        ajaxSpy.mockImplementation(()=> {
            return Promise.resolve('<div></div>');
        });
        let files = sdc_view.loadFilesFromController(ctr);
        expect(ajaxSpy).toBeCalledWith({
            type: 'get',
            url: 'TestCtr',
            data: {
                "VERSION": "0.0",
                "_method": "content",
            }
        });
    });

    test('adds 1 +3 to equal 4', () => {
        let ctr = new TestCtr();
        expect(ctr.contentUrl).toBe("TestCtr");
        expect(ctr.contentReload).toBe(false);
        expect(ctr.hasSubnavView).toBe(false);
    });

});