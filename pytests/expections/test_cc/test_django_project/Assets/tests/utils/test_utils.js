/**
 * @jest-environment jsdom
 */

import {app, AbstractSDC, controllerFactory, runControlFlowFunctions} from 'sdc';
import {jest} from '@jest/globals';
import $ from 'jquery';

window.$ = $;


/**
 * Returns a controller. This controller has been created by the using the normal SDC life cycle.
 *
 * @param app_name{string} Django app name
 * @param tag_name{string} Controller tag name (snake-case)
 * @param content_html{string} HTML: Mocked content of the controllers view template.
 * @param origen_html{string} HTML: Mocked content of the content in your target HTML container.
 * @returns {Promise<{instance, class}>}
 */
export async function get_controller(app_name, tag_name, content_html, origen_html = null) {
    let spy, Controller;
    const _register = app.register;
    spy = jest.spyOn(
        app,
        'register'
    );
    spy.mockImplementation(function (x) {
        Controller = x;
        _register(x);
    });


    let controller, parent = new AbstractSDC();

    let $c = $(document.createElement(tag_name));
    if (init_container) $c.append(init_container);
    $('body').append($c);
    const controller_flie_name = tag_name.replace(/[-]/, '_')
    await import(`../../src/${app_name}/controller/${controller_flie_name}/${controller_flie_name}.js`);

    const ajaxSpy = jest.spyOn($, 'ajax');
    ajaxSpy.mockImplementation(function () {
        return Promise.resolve(content_html);
    });

    controller = controllerFactory(parent, $c, tag_name, []);
    await runControlFlowFunctions(controller);

    ajaxSpy.mockRestore();
    spy.mockRestore();

    return {
        class: Controller,
        instance: controller
    }
}