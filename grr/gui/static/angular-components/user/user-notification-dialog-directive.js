'use strict';

goog.provide('grrUi.user.userNotificationDialogDirective.UserNotificationDialogController');
goog.provide('grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective');

goog.scope(function() {


/**
 * Controller for UserNotificationDialogDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.user.userNotificationDialogDirective.UserNotificationDialogController =
  function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.notificationUrl = 'users/me/notifications';
};

var UserNotificationDialogController = grrUi.user.userNotificationDialogDirective.UserNotificationDialogController;


/**
 * Directive for showing the notification dialog.
 *
 * @return {angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective = function() {
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
grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective.directive_name =
  'grrUserNotificationDialog';


});  // goog.scope
