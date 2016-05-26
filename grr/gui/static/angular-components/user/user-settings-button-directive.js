'use strict';

goog.provide('grrUi.user.userSettingsButtonDirective.UserSettingsButtonController');
goog.provide('grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective');


/**
 * Controller for UserSettingsButtonDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @param {!angular.$timeout} $timeout
 * @param {!angular.$window} $window
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.user.userSettingsButtonDirective.UserSettingsButtonController = function(
    $scope, $modal, $timeout, $window, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /** @private {!angular.$timeout} */
  this.timeout_ = $timeout;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {?boolean} */
  this.requestSent;

  /** @type {?boolean} */
  this.done;

  /** @type {?string} */
  this.error;

  /** @type {Object} */
  this.userSettings;
};
var UserSettingsButtonController =
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonController;


/**
 * Handles mouse clicks on itself.
 *
 * @export
 */
UserSettingsButtonController.prototype.onClick = function() {
  this.requestSent = false;
  this.done = false;
  this.error = undefined;

  this.userSettings = undefined;
  this.grrApiService_.getCached('users/me').then(function(response) {
    this.userSettings = response['data']['value']['settings'];
  }.bind(this));

  this.modal_.open({
    templateUrl: '/static/angular-components/user/' +
        'user-settings-button-modal.html',
    scope: this.scope_
  });
};


/**
 * Sends current settings value to the server and reloads the page after as
 * soon as server acknowledges the request afer a small delay. The delay is
 * needed so that the user can see the success message.
 *
 * @export
 */
UserSettingsButtonController.prototype.saveSettings = function() {
  var newUser = {
    type: 'GRRUser',
    value: {
      settings: this.userSettings
    }
  };
  this.grrApiService_.post('users/me', newUser, true).then(
      function success() {
        this.done = true;
        this.timeout_(this.window_.location.reload.bind(this.window_.location),
                      500);
      }.bind(this),
      function failure(response) {
        this.done = true;
        this.error = response.data.message || 'Unknown error.';
      }.bind(this));

  this.requestSent = true;
};

/**
 * UserSettingsButtonDirective renders a button that shows a dialog that allows
 * users to change their personal settings.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective =
    function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/user/' +
        'user-settings-button.html',
    controller: UserSettingsButtonController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective
    .directive_name = 'grrUserSettingsButton';
