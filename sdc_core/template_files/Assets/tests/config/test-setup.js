import {jest} from '@jest/globals';
import * as _sdc from 'sdc_client';
import $ from 'jquery';
import _ from 'lodash';

import { TextEncoder, TextDecoder } from 'util';

global['SCRIPT_OUTPUT'] = process.env.SCRIPT_OUTPUT.split("\n");
await new Promise(resolve => {
    $.get('/').then((res) => {
        for(let line of res.split('\n')) {
            line = line.trim();
            if(line.startsWith('window.')) {
                eval(line);
            }
        }
        resolve();
    }).catch((e) => {
        console.error(e);
    });
});

Object.assign(global, { TextDecoder, TextEncoder, $, jest, _sdc, _});