'use strict';

goog.module('grrUi.user.userLabelDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for UserLabelDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const UserLabelController =
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



/**
 * Directive that displays the notification button.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.UserLabelDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/user/user-label.html',
    controller: UserLabelController,
    controllerAs: 'controller'
  };
};

var UserLabelDirective = exports.UserLabelDirective;


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
UserLabelDirective.directive_name = 'grrUserLabel';


