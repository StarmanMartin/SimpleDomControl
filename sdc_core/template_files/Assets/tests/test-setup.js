import {jest} from '@jest/globals';
import * as _sdc from 'sdc_client';
import $ from 'jquery';
import { TextEncoder, TextDecoder } from 'util';

Object.assign(global, { TextDecoder, TextEncoder, $, jest, _sdc});