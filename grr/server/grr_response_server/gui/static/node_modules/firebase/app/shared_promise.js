/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});
var scope = void 0;
if (typeof global !== 'undefined') {
    scope = global;
} else if (typeof self !== 'undefined') {
    scope = self;
} else {
    try {
        scope = Function('return this')();
    } catch (e) {
        throw new Error('polyfill failed because global object is unavailable in this environment');
    }
}
var PromiseImpl = scope.Promise || require('promise-polyfill');
var local = exports.local = {
    Promise: PromiseImpl,
    GoogPromise: PromiseImpl
};
