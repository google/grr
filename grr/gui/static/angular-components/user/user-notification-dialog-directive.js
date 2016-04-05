'use strict';

goog.provide('grrUi.user.userNotificationDialogDirective.UserNotificationDialogController');
goog.provide('grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective');

goog.scope(function() {

var module = grrUi.user.userNotificationDialogDirective;


/**
 * Controller for UserNotificationDialogDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
module.UserNotificationDialogController =
  function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.notificationUrl = 'users/me/notifications';
};

var UserNotificationDialogController = module.UserNotificationDialogController;


/**
 * Directive for showing the notification dialog.
 *
 * @constructor
 * @ngInject
 * @export
 */
module.UserNotificationDialogDirective = function() {
  return {
    scope: {
      close: '&'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/user/user-notification-dialog.html',
    controller: UserNotificationDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
module.UserNotificationDialogDirective.directive_name =
  'grrUserNotificationDialog';


});  // goog.scope