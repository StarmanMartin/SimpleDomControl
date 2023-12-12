import {AbstractSDC, app} from 'sdc_client';


export class SdcUpdateOnChangeController extends AbstractSDC {

    constructor() {
        super();

        this._timer = null;
        this.isAutoChange = true;
        this._isNotReady = true;
        this._isChanged = false;
        this._lastTimeChanged = '';

        this.events.unshift({
            'change': {
                '.timer-change': this.change
            },
            'keydown': {
                '.timer-change':  this.startTimer
            }

        });
    }

    //-------------------------------------------------//
    // Lifecycle handler                               //
    // - onInit (tag parameter)                        //
    // - onLoad (DOM not set)                          //
    // - willShow  (DOM set)                           //
    // - onRefresh  (recalled on reload)              //
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

    onRefresh() {
        this._isNotReady = true;
        setTimeout(()=> {
            this._isNotReady = false;
        }, 500);
        return super.onRefresh();
    }

    /*setUpFileUploat($form) {
        let $file_container = $form.find('input[type=file]').parent();
        $file_container.each(function () {
            let $link = $(this).find('a');
            let $img = $('<img class="image-preview-upload">');
            $img.attr('src', $link.attr('href'));
            $link.attr('target', '_blank').addClass('image-preview-upload-container').html($img);

            $(this).find('input[type=checkbox]').addClass('timer-change clear-check-box');

        });
    };*/

    change(elem) {
        if (!this.isAutoChange || this._isNotReady) {
            return;
        }

        if (this._timer) {
            clearTimeout(this._timer);
            this._timer = null;
        }

        if(!this._lastTimeChanged !== elem.name) {
            this.onChange($(elem));
            this._isChanged = true;
            this._lastTimeChanged = '';
        }
    }

    startTimer(elem) {
        if (!this.isAutoChange || this._isNotReady) {
            return;
        }

        if (this._timer) {
            clearTimeout(this._timer);
            this._timer = null;
        }
        this._lastTimeChanged = '';
        this._isChanged = false;
        this._timer = setTimeout(()=> {
            if (!this._isChanged) {
                this.onChange($(elem));
                this._lastTimeChanged = elem.name;
            }
        }, 1000);

    }

}

app.register(SdcUpdateOnChangeController);