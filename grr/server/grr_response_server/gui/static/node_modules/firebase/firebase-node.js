/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
var firebase = require('./app-node');
require('./auth-node');

require('./server-auth-node');
require('./database-node');
var Storage = require('dom-storage');
var XMLHttpRequest = require("xmlhttprequest").XMLHttpRequest;
firebase.INTERNAL.extendNamespace({
    'INTERNAL': {
        'node': {
            'localStorage': new Storage(null, { strict: true }),
            'sessionStorage': new Storage(null, { strict: true }),
            'XMLHttpRequest': XMLHttpRequest
        }
    }
});
var AsyncStorage;

exports.default = firebase;
module.exports = exports['default'];
