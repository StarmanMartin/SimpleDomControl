import {jest} from '@jest/globals';
import * as _sdc from 'sdc_client';
import $ from 'jquery';
import _ from 'lodash';

import {TextEncoder, TextDecoder} from 'util';

global.SCRIPT_OUTPUT = process.env.SCRIPT_OUTPUT.split("\n");
global.gettext = (x) => x;

if (!File.prototype.arrayBuffer) {
  File.prototype.arrayBuffer = function () {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        resolve(reader.result);
      }
      reader.onerror = reject;
      reader.readAsArrayBuffer(this);
    });
  };
}

if (!File.prototype.text) {
  File.prototype.text = function () {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        resolve(reader.result);
      }
      reader.onerror = reject;
      reader.readAsText(this);
    });
  };
}

await new Promise(resolve => {
  $.get('/').then((res) => {
    for (let line of res.split('\n')) {
      line = line.trim();
      if (line.startsWith('window.')) {
        eval(line);
      }
    }
    resolve();
  }).catch((e) => {
    console.error(e);
  });
});

Object.assign(global, {TextDecoder, TextEncoder, $, jest, _sdc, _});