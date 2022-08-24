import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class ChangeSyncMixinController extends AbstractSDC {

    constructor() {
        super();
         //<change-sync-mixin></change-sync-mixin>

        this._timer = null;
        this.isAutoChange = true;
        this._isChanged = false;

        this.events.unshift({
            '.timer-change': {
                change: this.change,
                keydown: this.startTimer
            }
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

    clearErrorsInForm($form) {
        $form.find('.has-error').removeClass('has-error').find('.alert-danger').remove();
    }

    setErrorsInForm = function ($form, $resForm) {
        if (!$resForm.is('form')) {
            $resForm = $resForm.find('form');
        }

        $form.attr('action', $resForm.attr('action'));
        $form.find('.has-error').removeClass('has-error').find('.alert-danger').remove();
        let $file_container = $resForm.find('input[type=file]').parent();
        $form.find('input[type=file]').parent().each(function (index) {
            $(this).replaceWith($file_container[index]);
        });

        let hasNoError = true;

        $resForm.find('.has-error').each(function () {
            hasNoError = false;
            let $resErrorField = $(this);
            let className = $resErrorField.data('auto-id');
            let $errorField = $form.find('.form-group.' + className);
            $errorField.addClass('has-error');
            $errorField.find('.form-input-container').append($resErrorField.find('.alert-danger'));
        });

        return hasNoError;
    };

    change(elem) {
        if (!this.isAutoChange) {
            return;
        }

        if (this._timer) {
            clearTimeout(this._timer);
            this._timer = null;
        }
        if (!this._isChanged) {
            this.onChange($(elem));
            this._isChanged = true;
        }
    }

    startTimer(elem) {
        if (!this.isAutoChange) {
            return;
        }

        if (this._timer) {
            clearTimeout(this._timer);
            this._timer = null;
        }
        this._isChanged = false;
        this._timer = setTimeout(()=> {
            if (!this._isChanged) {
                this.onChange($(elem));
                this._isChanged = true;
            }
        }, 1000);

    }
}

app.register(ChangeSyncMixinController);