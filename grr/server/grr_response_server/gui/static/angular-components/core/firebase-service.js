goog.module('grrUi.core.firebaseService');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Service for doing GRR Firebase setup.
 * @export
 * @unrestricted
 */
exports.FirebaseService = class {
  /**
   * @param {!angular.$http} $http The Angular http service.
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($http, grrApiService) {
    /** @private {angular.$http} */
    this.http_ = $http;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;
  }

  /**
   * Sets up redirect-based Firebase authentication if a Firebase app is
   * configured inside GRR (this happens when AdminUI.firebase_api_key and
   * AdminUI.firebase_auth_domain configuration keys are set.
   *
   * @export
   */
  setupIfNeeded() {
    if (angular.isUndefined(window.firebase) || firebase.apps.length == 0) {
      this.grrApiService_.markAuthDone();
      return;
    }

    var firebaseError;
    firebase.auth()
        .getRedirectResult()
        .then(function(result) {
          // We don't have to do anything when redirect is successful.
          // onAuthStateChanged callback is responsible for this case.
        }.bind(this))
        .catch(function(error) {
          firebaseError = error;
          // Marking auth as done, letting the grrApiService to proceed with API
          // requests, which will inevitably fail. Failing requests would be
          // indicated in the UI, so the user will be aware of the issue.
          this.grrApiService_.markAuthDone();
        }.bind(this));

    // Listening for auth state changes.
    firebase.auth().onAuthStateChanged(function(user) {
      if (user) {
        user.getToken().then(function(token) {
          this.http_.defaults.headers['common']['Authorization'] =
              'Bearer ' + token;
          this.grrApiService_.markAuthDone();
        }.bind(this));
      } else if (!firebaseError) {
        var providerName = firebase.apps[0].options['authProvider'];
        var provider = new firebase.auth[providerName]();
        firebase.auth().signInWithRedirect(provider);
      }
    }.bind(this));
  }
};
var FirebaseService = exports.FirebaseService;


/**
 * Name of the service in Angular.
 */
FirebaseService.service_name = 'grrFirebaseService';
