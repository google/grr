'use strict';

goog.module('grrUi.core.globalNotificationsDirective');
goog.module.declareLegacyNamespace();



var SECOND = 1000;
var FETCH_INTERVAL = 60 * SECOND;


/**
 * Controller for GlobalNotificationsDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const GlobalNotificationsController =
    function($scope, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array} */
  this.globalNotifications = [];

  /** private {angular.$q.Promise} */
  this.intervalPromise_;

  // Immediately fetch global notifications.
  this.fetchGlobalNotifications_();

  // Refetch pending notification count every FETCH_INTERVAL ms.
  this.intervalPromise_ = this.interval_(
    this.fetchGlobalNotifications_.bind(this), FETCH_INTERVAL);
  this.scope_.$on('$destroy', this.stopPollingGlobalNotifications_.bind(this));
};


/**
 * Polls global notifications from the server.
 *
 * @private
 */
GlobalNotificationsController.prototype.fetchGlobalNotifications_ =
    function() {
  this.grrApiService_.get('users/me/notifications/pending/global').then(
    function(response){
      this.globalNotifications = response.data['items'];
    }.bind(this));
};

/**
 * Deletes a global notification.
 *
 * @export
 */
GlobalNotificationsController.prototype.deleteGlobalNotification =
    function(notification) {
  // Delete it from the collection immediately for better user feedback.
  var index = this.globalNotifications.indexOf(notification);
  this.globalNotifications.splice(index, 1);

  var type = notification['value']['type']['value'];
  var url = 'users/me/notifications/pending/global/' + type;
  this.grrApiService_.delete(url);
};

/**
 * Polls global notifications from the server.
 *
 * @private
 */
GlobalNotificationsController.prototype.stopPollingGlobalNotifications_ =
    function() {
  this.interval_.cancel(this.intervalPromise_);
};

/**
 * Directive that displays a button whenever a server error occurs
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.GlobalNotificationsDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/core/global-notifications.html',
    controller: GlobalNotificationsController,
    controllerAs: 'controller'
  };
};

var GlobalNotificationsDirective = exports.GlobalNotificationsDirective;

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
GlobalNotificationsDirective.directive_name = 'grrGlobalNotifications';

/**
 * The fetch interval for global notifications.
 *
 * @const
 * @export
 */
GlobalNotificationsDirective.fetch_interval = FETCH_INTERVAL;

