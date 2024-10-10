import {AbstractSDC, app} from 'sdc_client';


export class SdcSearchViewController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/sdc_search_view"; //<sdc-search-view></sdc-search-view>

        this.isRange = true;
        this.isTotalCount = true;
        this.dataIdxKey = 'next-idx';
        this.id = `${new Date().getTime()}_${Math.random().toString(36).substring(7)}`;
        this.$form = null;
        this.events.unshift({
            'submit': {
                '.search-form': (form, ev) => {
                    ev.preventDefault();
                }
            },
            'click': {
                '.page-number-control-btn': function (btn) {
                    this.$form[0].range_start.value = $(btn).data(this.dataIdxKey);
                    this.onChange();
                }
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

    onInit(url, rangeSize, rangeStart, rangeEnd, totalCount, removeLabels) {
        this.url = url || '';
        if (typeof rangeStart === 'undefined' || typeof rangeEnd === 'undefined') {
            this.isRange = false;
        } else {
            if (typeof rangeSize === 'undefined') {
                rangeSize = rangeEnd - rangeStart
            }
            if (typeof totalCount === 'undefined') {
                this.isTotalCount = false;
            }

            this.totalCount = totalCount;
            this.rangeSize = rangeSize;
            this.range = [rangeStart - rangeSize - 1, rangeStart, rangeEnd];
            if (rangeStart <= 1 && rangeEnd >= totalCount) {
                this.isRange = false;
            }
        }

        this.removeLabels = removeLabels || false;
    };

    onLoad($html) {
        this.$form = $(document.createElement('form'));
        $html.find('.inner-form.search-form').append(this.$container.html());
        this.$form.append(this.$container.html());
        this.$form.attr('action', this.url);
        this.$form.attr('method', 'post');
        this.$form.attr('id', this.id);
        return super.onLoad($html);
    }

    willShow() {
        let $pageContainer = this.find('.page-number-control');

        this.find('.form-group').addClass('form-group-sm');

        if (this.removeLabels) {
            //this.find('.control-label[for=id_search]').parent().remove();
            this.find('.form-input-container').removeClass('col-md-7');
            this.find('.form-group').addClass('no-label');

        }

        if (!this.isRange) {
            $pageContainer.remove();
            return super.willShow();
        }

        $pageContainer.find('.range-span').text(this.range[1] + ' - ' + this.range[2]);
        if (this.isTotalCount) {
            $pageContainer.find('.total-amount-span').text(' / ' + this.totalCount);
        } else {
            $pageContainer.find('.total-amount-span').remove();
        }

        if (this.range[1] > 1) {
            $pageContainer.find('.page-number-control-btn-prev').data(this.dataIdxKey, this.range[0]);
        } else {
            $pageContainer.find('.page-number-control-btn-prev').addClass('disabled').prop("disabled", true);
        }

        if (this.range[2] < this.totalCount) {
            $pageContainer.find('.page-number-control-btn-next').data(this.dataIdxKey, this.range[2]);
        } else {
            $pageContainer.find('.page-number-control-btn-next').addClass('disabled').prop("disabled", true);
        }
        return super.willShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    onChange() {
        let _origenForm = this.find('.inner-form.search-form');
        this.$form.find('.form-control').each(function () {
            if (this.id !== '') {
                let $elem = _origenForm.find(`#${this.id}`);
                if (this.tagName === 'SELECT') {
                    let $this = $(this);
                    $this.empty();
                    $this.append(`<option value="${$elem.val()}" selected">`);
                } else {
                    $(this).val($elem.val());
                }
            }
        });
        if (!this._parentController.onSearch) {
            console.error('SearchController parent needs to implement onSearch(form)');
            return;
        }

        this._parentController.onSearch(this.$form[0]);
    };
}

app.register(SdcSearchViewController).addMixin('sdc-update-on-change');