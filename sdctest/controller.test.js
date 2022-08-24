var ac = require('../lib/AbstractSDC.js')

class TestCtr extends ac.AbstractSDC{
    constructor() {
        super();
        this.contentUrl = 'TestCtr'; //<test-ctr>
        this._cssUrls.push('TestCtr.css');
        this.events.unshift({

        });
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

test('adds 1 +3 to equal 4', () => {
    let ctr = new TestCtr();
    expect(ctr.contentUrl).toBe("TestCtr");
    expect(ctr.contentReload).toBe(false);
    expect(ctr.hasSubnavView).toBe(false);
    expect(ctr.cssUrls).toContain("TestCtr.css");
});