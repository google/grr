/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
var firebase = require('./app');
require('./auth');
var Storage, XMLHttpRequest;

require('./database');
require('./storage');

var AsyncStorage = require('react-native').AsyncStorage;
firebase.INTERNAL.extendNamespace({
    'INTERNAL': {
        'reactNative': {
            'AsyncStorage': AsyncStorage
        }
    }
});

exports.default = firebase;
module.exports = exports['default'];
