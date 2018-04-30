'use strict';

goog.module('grrUi.user.userNotificationButtonDirective');
goog.module.declareLegacyNamespace();



var SECOND = 1000;

// This interval will be used by the notification button and the desktop
// notifications directive to refetch the notifications.
var FETCH_INTERVAL = 10 * SECOND;


/**
 * Controller for UserNotificationButtonDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const UserNotificationButtonController =
  function($scope, $interval, $uibModal, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {number} */
  this.notificationCount = 0;

  // Immediately fetch pending notification count.
  this.fetchNotificationCount_();

  // Refetch pending notification count every FETCH_INTERVAL ms.
  this.interval_(this.fetchNotificationCount_.bind(this), FETCH_INTERVAL);
};



/**
 * Fetches the number of pending notifications.
 *
 * @private
 */
UserNotificationButtonController.prototype.fetchNotificationCount_ = function() {
  this.grrApiService_.get('users/me/notifications/pending/count').then(function(response){
    this.notificationCount = response.data['count'];
  }.bind(this));
};

/**
 * Shows the notification dialog.
 *
 * @export
 */
UserNotificationButtonController.prototype.showNotifications = function() {
  var modalScope = this.scope_.$new();

  var modalInstance = this.uibModal_.open({
    template: '<grr-user-notification-dialog close="$close()" />',
    scope: modalScope,
    size: 'lg'
  });

  modalInstance.result.finally(function() {
    this.notificationCount = 0;
  }.bind(this));
};


/**
 * Directive that displays the notification button.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.UserNotificationButtonDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/user/user-notification-button.html',
    controller: UserNotificationButtonController,
    controllerAs: 'controller'
  };
};

var UserNotificationButtonDirective = exports.UserNotificationButtonDirective;


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
UserNotificationButtonDirective.directive_name = 'grrUserNotificationButton';

/**
 * Notification fetch interval.
 *
 * @const
 * @export
 */
UserNotificationButtonDirective.fetch_interval = FETCH_INTERVAL;


