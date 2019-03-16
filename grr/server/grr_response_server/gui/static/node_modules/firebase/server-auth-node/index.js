/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

var Auth = require('./auth.js');
var firebase = require('../app-node');

var serviceFactory = function(app, extendApp) {
  var auth = new Auth(app);
  extendApp({
    'INTERNAL': {
      'getToken': auth.INTERNAL.getToken.bind(auth),
      'addAuthTokenListener': auth.INTERNAL.addAuthTokenListener.bind(auth),
      'removeAuthTokenListener': auth.INTERNAL.removeAuthTokenListener.bind(auth)
    }
  });
  return auth;
};

function appHook(event, app) {
  if (event === 'create') {
    app.auth();
  }
}

module.exports = firebase.INTERNAL.registerService(
  'serverAuth',
  serviceFactory,
  {'Auth': Auth},
  appHook);
