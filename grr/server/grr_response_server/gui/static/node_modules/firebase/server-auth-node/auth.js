/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

var FirebaseTokenGenerator = require('./token-generator');
var fs = require('fs');
var firebase = require('../app-node');
var credential = require('./credential.js');

function getServiceAccount(app_) {
  var serviceAccountPathOrObject = typeof app_.options.serviceAccount === 'undefined' ?
    process.env.GOOGLE_APPLICATION_CREDENTIALS :
    app_.options.serviceAccount;
  var serviceAccount;
  if (typeof serviceAccountPathOrObject === 'undefined') {
    return null;
  } else if (typeof serviceAccountPathOrObject === 'string') {
    try {
      serviceAccount = JSON.parse(fs.readFileSync(serviceAccountPathOrObject, 'utf8'));
    } catch (error) {
      throw new Error('Failed to parse service account key file: ' + error);
    }
  } else if (typeof serviceAccountPathOrObject === 'object') {
    serviceAccount = {};

    var projectId = serviceAccountPathOrObject.project_id || serviceAccountPathOrObject.projectId;
    if (typeof projectId !== 'undefined') {
      serviceAccount.project_id = projectId;
    }

    var privateKey = serviceAccountPathOrObject.private_key || serviceAccountPathOrObject.privateKey;
    if (typeof privateKey !== 'undefined') {
      serviceAccount.private_key = privateKey;
    }

    var clientEmail = serviceAccountPathOrObject.client_email || serviceAccountPathOrObject.clientEmail;
    if (typeof clientEmail !== 'undefined') {
      serviceAccount.client_email = clientEmail;
    }
  } else {
    throw new Error('Invalid service account provided');
  }

  if (typeof serviceAccount.private_key !== 'string' || !serviceAccount.private_key) {
    throw new Error('Service account must contain a "private_key" field');
  } else if (typeof serviceAccount.client_email !== 'string' || !serviceAccount.client_email) {
    throw new Error('Service account must contain a "client_email" field');
  }

  return serviceAccount;
}

var Auth = function(app_) {
  if (!('options' in app_)) {
    throw new Error('First parameter to Auth constructor must be an instance of firebase.App');
  }

  var cachedToken_ = null;
  var tokenListeners_ = [];

  var credential_ = app_.options.credential;
  var serviceAccount_ = getServiceAccount(app_);
  var tokenGenerator_;

  if (credential_ && typeof credential_.getAccessToken !== 'function') {
    throw new Error('Called firebase.initializeApp with an invalid credential parameter');
  }
  if (serviceAccount_) {
    credential_ = credential_ || new credential.CertCredential(serviceAccount_);
    tokenGenerator_ = new FirebaseTokenGenerator(serviceAccount_);
  } else {
    credential_ = credential_ || new credential.UnauthenticatedCredential();
  }

  Object.defineProperty(this, 'app', {
    get: function() { return app_; }
  });

  this.createCustomToken = function(uid, developerClaims) {
    console.log(
      'createCustomToken() is deprecated and will be removed in the next major version. You ' +
      'should instead use the same method in the `firebase-admin` package. See ' +
      'https://firebase.google.com/docs/admin/setup for details on how to get started.'
    );

    if (typeof tokenGenerator_ === 'undefined') {
      throw new Error('Must initialize FirebaseApp with a service account to call auth().createCustomToken()');
    }
    return tokenGenerator_.createCustomToken(uid, developerClaims);
  };

  this.verifyIdToken = function(idToken) {
    console.log(
      'verifyIdToken() is deprecated and will be removed in the next major version. You ' +
      'should instead use the same method in the `firebase-admin` package. See ' +
      'https://firebase.google.com/docs/admin/setup for details on how to get started.'
    );

    if (typeof tokenGenerator_ === 'undefined') {
      throw new Error('Must initialize FirebaseApp with a service account to call auth().verifyIdToken()');
    }
    return tokenGenerator_.verifyIdToken(idToken);
  };

  this.INTERNAL = {};

  this.INTERNAL.delete = function() {
    return firebase.Promise.resolve();
  };

  this.INTERNAL.getToken = function(forceRefresh) {
    var expired = cachedToken_ && cachedToken_.expirationTime < Date.now();
    if (cachedToken_ && !forceRefresh && !expired) {
      return firebase.Promise.resolve(cachedToken_);
    } else {
      return firebase.Promise.resolve().then(function() {
        return credential_.getAccessToken();
      }).then(function(result) {
        if (result === null) {
          return null;
        }
        if (typeof result !== 'object' ||
            typeof result.expires_in !== 'number' ||
            typeof result.access_token !== 'string') {
          throw new Error('firebase.initializeApp was called with a credential ' +
              'that creates invalid access tokens: ' + JSON.stringify(result));
        }
        var token = {
          accessToken: result.access_token,
          expirationTime: Date.now() + (result.expires_in * 1000)
        };

        var hasAccessTokenChanged = (cachedToken_ && cachedToken_.accessToken !== token.accessToken);
        var hasExpirationTimeChanged = (cachedToken_ && cachedToken_.expirationTime !== token.expirationTime);
        if (!cachedToken_ || hasAccessTokenChanged || hasExpirationTimeChanged) {
          cachedToken_ = token;
          tokenListeners_.forEach(function(listener) {
            listener(token.accessToken);
          });
        }

        return token;
      });
    }
  };

  this.INTERNAL.addAuthTokenListener = function(listener) {
    tokenListeners_.push(listener);
    if (cachedToken_) {
      listener(cachedToken_);
    }
  };

  this.INTERNAL.removeAuthTokenListener = function(listener) {
    tokenListeners_ = tokenListeners_.filter(function(other) {
      return other !== listener;
    });
  };
};

module.exports = Auth;

