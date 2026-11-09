import {AbstractSDC, app, trigger, on} from 'sdc_client';

/**
 * True if ``branch`` matches one of the ``allowedPaths`` patterns, or if there are none.
 *
 * ``branch`` lists the tags of the views in front of a view, outermost first (for ``/~dashboard~settings`` the
 * branch of ``settings`` is ``['dashboard']``). A pattern is an array of tags that must match the whole branch;
 * ``'*'`` matches exactly one view, ``'**'`` any number of views (also none).
 *
 * - ``[]`` (no patterns): allowed everywhere
 * - ``[[]]``: only at the top (no views in front)
 * - ``[['dashboard']]``: only directly below a top-level ``dashboard``
 * - ``[['**', 'dashboard']]``: directly below a ``dashboard`` at any depth
 * - ``[['*']]``: below exactly one view of any kind
 *
 * @param {Array<Array<string>>} allowedPaths - patterns
 * @param {Array<string>} branch - tags of the views in front, outermost first
 * @return {boolean}
 */
export function matchesAllowedPaths(allowedPaths, branch) {
  if (!Array.isArray(allowedPaths) || allowedPaths.length === 0) {
    return true;
  }
  const match = (pattern, i, j) => {
    if (i === pattern.length) {
      return j === branch.length;
    }
    if (pattern[i] === '**') {
      return match(pattern, i + 1, j) || (j < branch.length && match(pattern, i, j + 1));
    }
    return j < branch.length && (pattern[i] === '*' || pattern[i] === branch[j]) && match(pattern, i + 1, j + 1);
  };
  return allowedPaths.some((pattern) => Array.isArray(pattern) && match(pattern, 0, 0));
}

export class SdcNavigationClientController extends AbstractSDC {

  constructor() {
    super();
    //<sdc-navigation-client></sdc-navigation-client>
    this.menu_id = 0;
    this._navController = null;
    /**
     * Where the view may be opened by the ``<sdc-navigator>``: patterns of the views in front of it, outermost
     * first; ``'*'`` = exactly one view, ``'**'`` = any number of views (see ``matchesAllowedPaths``). A view
     * opened elsewhere shows ``sdc-error 403`` ("Not allowed") instead. Empty (default): allowed everywhere.
     * Override it in the controller's constructor, e.g. ``this.allowedPaths = [['**', 'dashboard']];``.
     *
     * @type {Array<Array<string>>}
     */
    this.allowedPaths = [];

    /**
     * Events is an array of dom events.
     * The pattern is {'event': {'dom_selector': handler}}
     * Uncommend the following line to add events;
     */
    // this.events.unshift({'click': {'.header-sample': (ev, $elem)=> $elem.css('border', '2px solid black')}}});
  }

  //-------------------------------------------------//
  // Lifecycle handler                               //
  // - onLoad (DOM not set)                          //
  // - willShow  (DOM set)                           //
  // - onRefresh  (recalled on reload)              //
  //-------------------------------------------------//
  // - onRemove                                      //
  //-------------------------------------------------//

  onLoad($html) {
    on('_onResize', this);
    return super.onLoad($html);
  }

  willShow() {
    this.confirmPageLoaded();
    return super.willShow();
  }

  _onResize() {
    this.onResize();
  }

  onResize() {

  }

  confirmPageLoaded() {
    trigger('navLoaded', this);
    trigger('changeMenu', this.menu_id);

  }

  get navController() {
    return this._navController?.deref();
  }

  get activeController() {
    return this._navController?.deref().activeController;
  }

  get navControllerPath() {
    return this._navController?.deref()._origin_target;
  }

}

app.register(SdcNavigationClientController);