/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

var https = require('https');
var jwt = require('jsonwebtoken');
var firebase = require('../app-node');

var GOOGLE_TOKEN_AUDIENCE = 'https://accounts.google.com/o/oauth2/token';
var GOOGLE_AUTH_TOKEN_HOST = 'accounts.google.com';
var GOOGLE_AUTH_TOKEN_PATH = '/o/oauth2/token';
var GOOGLE_AUTH_TOKEN_PORT = 443;

var ONE_HOUR_IN_SECONDS = 60 * 60;
var JWT_ALGORITHM = 'RS256';

var Credential = function() {};

var AccessToken = function() {};

var ServiceAccount = function() {};

Credential.prototype.getAccessToken = function() {};

var CertCredential = function(serviceAccount) {
  this.serviceAccount_ = serviceAccount;
};

CertCredential.prototype.getAccessToken = function() {
  var token = this.authJwt();
  return new firebase.Promise(function(resolve, reject) {
    var postData = 'grant_type=urn%3Aietf%3Aparams%3Aoauth%3A' +
        'grant-type%3Ajwt-bearer&assertion=' +
        token;
    var options = {
      method: 'POST',
      host: GOOGLE_AUTH_TOKEN_HOST,
      port: GOOGLE_AUTH_TOKEN_PORT,
      path: GOOGLE_AUTH_TOKEN_PATH,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': postData.length
      }
    };
    var req = https.request(options, function(res) {
      var buffers = [];
      res.on('data', function(buffer) {
        buffers.push(buffer);
      });
      res.on('end', function() {
        try {
          var json = JSON.parse(Buffer.concat(buffers));
          if (json.error) {
            var msg = 'Error refreshing access token: ' + json.error;
            if (json.error_description) {
              msg += ' (' + json.error_description + ')';
            }
            reject(new Error(msg));
          } else if (!json.access_token || !json.expires_in) {
            reject(new Error('Unexpected response from OAuth server'));
          } else {
            resolve(json);
          }
        } catch (err) {
          reject(err);
        }
      });
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
};

CertCredential.prototype.authJwt = function() {
  var claims = {
    scope: [
      'https://www.googleapis.com/auth/userinfo.email',
      'https://www.googleapis.com/auth/firebase.database',
    ].join(' ')
  };
  return jwt.sign(claims, this.serviceAccount_.private_key, {
    audience: GOOGLE_TOKEN_AUDIENCE,
    expiresIn: ONE_HOUR_IN_SECONDS,
    issuer: this.serviceAccount_.client_email,
    algorithm: JWT_ALGORITHM
  });
};

var UnauthenticatedCredential = function() {};

UnauthenticatedCredential.prototype.getAccessToken = function() {
  return firebase.Promise.resolve(null);
};

module.exports.Credential = Credential;
module.exports.CertCredential = CertCredential;
module.exports.UnauthenticatedCredential = UnauthenticatedCredential;

