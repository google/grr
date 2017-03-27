'use strict';

goog.provide('grrUi.user.userLabelDirective.UserLabelController');
goog.provide('grrUi.user.userLabelDirective.UserLabelDirective');


goog.scope(function() {

/**
 * Controller for UserLabelDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.user.userLabelDirective.UserLabelController =
  function($scope, grrApiService) {

    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!grrUi.core.apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @type {string} */
    this.username;

    /** @type {string} */
    this.error;

    this.grrApiService_.getCached('users/me').then(function(response) {
      this.username = response.data['value']['username']['value'];
    }.bind(this), function(error) {
      if (error['status'] == 403) {
        this.error = 'Authentication Error';
      } else {
        this.error = error['statusText'] || ('Error');
      }
    }.bind(this));
  };

var UserLabelController =
  grrUi.user.userLabelDirective.UserLabelController;


/**
 * Directive that displays the notification button.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.user.userLabelDirective.UserLabelDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/user/user-label.html',
    controller: UserLabelController,
    controllerAs: 'controller'
  };
};

var UserLabelDirective =
  grrUi.user.userLabelDirective.UserLabelDirective;


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
UserLabelDirective.directive_name = 'grrUserLabel';


});  // goog.scope
