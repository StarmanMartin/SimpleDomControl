import {AbstractSDC} from '../../../simpleDomControl/AbstractSDC.js';
import {app} from '../../../simpleDomControl/sdc_main.js';


class SearchControllerController extends AbstractSDC {

    constructor() {
        super();
        this.contentUrl = "/sdc_view/sdc_tools/search_controller"; //<search-controller></search-controller>
        this._cssUrls.push('/static/sdc_tools/css/sdc/search_controller.css');

        this.isRange = true;
        this.isTotalCount = true;
        this.dataIdxKey = 'next-idx';
        this.id = `${new Date().getTime()}_${Math.random().toString(36).substring(7)}`;
        this.$form = null;
        this.events.unshift({
            'submit': {
                '.search-form' : (form, ev) => {
                    ev.preventDefault();
                }
            },
            'click': {
                '.page-number-control-btn': function (btn) {
                    let index = $(btn).data(this.dataIdxKey);
                    this.find('#id_range_start').val(index);
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
    // - afterShow  (recalled on reload)               //
    //-------------------------------------------------//
    // - onRefresh                                     //
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
        this.$form = $html.find('form');
        this.$form.append(this.$container.html());
        this.$form.attr('action', this.url);
        this.$form.attr('id', this.id);
        return super.onLoad($html);
    }

    willShow() {
        return super.willShow();
    }

    afterShow () {
        let $pageContainer = this.find('.page-number-control');

        this.find('.form-group').addClass('form-group-sm')

        if (this.removeLabels) {
            this.find('.control-label[for=id_search]').parent().remove();
            this.find('.form-input-container').removeClass('col-md-7');
            this.find('.form-group.id_order_by').addClass('no-label');

        }

        if (!this.isRange) {
            $pageContainer.remove();
            return
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
            $pageContainer.find('.page-number-control-btn-prev').remove();
        }

        if (this.range[2] < this.totalCount) {
            $pageContainer.find('.page-number-control-btn-next').data(this.dataIdxKey, this.range[2]);
        } else {
            $pageContainer.find('.page-number-control-btn-next').remove();
        }
        return super.afterShow();
    }

    onRefresh() {
        return super.onRefresh();
    }

    onChange () {
        if (!this._parentController.onSearch) {
            console.error('SearchController parent needs to implement onSearch(form)');
            return;
        }

        this._parentController.onSearch(this.$form[0]);
    };

}

app.register(SearchControllerController).addMixin('change-sync-mixin');