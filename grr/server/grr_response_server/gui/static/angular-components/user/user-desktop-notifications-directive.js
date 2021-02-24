goog.module('grrUi.user.userDesktopNotificationsDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const timeService = goog.requireType('grrUi.core.timeService');
const {UserNotificationButtonDirective} = goog.require('grrUi.user.userNotificationButtonDirective');
const {annotateApiNotification, openReference} = goog.require('grrUi.user.userNotificationItemDirective');



document.addEventListener('DOMContentLoaded', function() {
  if (typeof Notification !== 'undefined' &&
      Notification.permission !== 'granted') {
    Notification.requestPermission();
  }
});

/** @const */
var FETCH_INTERVAL = UserNotificationButtonDirective.fetch_interval;

/** @const */
var MAX_DISPLAYED_NOTIFICATIONS = 2;


/**
 * Controller for UserDesktopNotificationsDirective.
 * @unrestricted
 */
const UserDesktopNotificationsController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$interval} $interval
   * @param {!angular.$window} $window
   * @param {!angular.$location} $location
   * @param {!apiService.ApiService} grrApiService
   * @param {!timeService.TimeService} grrTimeService
   * @ngInject
   */
  constructor(
      $scope, $interval, $window, $location, grrApiService, grrTimeService) {
    if (typeof Notification === 'undefined') {
      return;  // Nothing to do here..
    }

    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$interval} */
    this.interval_ = $interval;

    /** @private {!angular.$window} */
    this.window_ = $window;

    /** @private {!angular.$location} */
    this.location_ = $location;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {timeService.TimeService} grrTimeService */
    this.timeService_ = grrTimeService;

    /** @private {Array.<Object>} */
    this.notifications_ = [];

    /** @private {number} */
    this.lastTimestamp_ = this.timeService_.getCurrentTimeMs() * 1000;

    // Refetch pending notifications every FETCH_INTERVAL ms.
    this.interval_(this.fetchPendingNotifications_.bind(this), FETCH_INTERVAL);
  }

  /**
   * Displays a desktop notification.
   *
   * @private
   *
   * @param {string} title The displayed notification's title.
   * @param {string} body The displayed notification's body text.
   * @param {string} tag A string that uniquely identifies the notification
   across browser windows.
   * @param {function()=} opt_onclick Optional on notification click callback.
   * @return {!Object} Generated Notification instance.
   */
  notify_(title, body, tag, opt_onclick) {
    var notification = new Notification(title, {
      body: body,
      icon: 'static/images/grr_logo_notification.png',
      tag: tag,
    });

    notification.onclick = function() {
      this.window_.focus();
      notification.close();

      if (angular.isDefined(opt_onclick)) {
        opt_onclick();
      }
    }.bind(this);

    this.notifications_.push(notification);

    if (this.notifications_.length > MAX_DISPLAYED_NOTIFICATIONS) {
      this.notifications_.shift().close();
    }

    return notification;
  }

  /**
   * Fetches pending notifications.
   *
   * @private
   */
  fetchPendingNotifications_() {
    this.grrApiService_
        .get('users/me/notifications/pending', {timestamp: this.lastTimestamp_})
        .then(function(response) {
          var items = response['data']['items'];
          if (items.length == 0) {
            return;
          }

          items.sort(function(lhs, rhs) {
            return lhs['value']['timestamp']['value'] -
                rhs['value']['timestamp']['value'];
          });

          this.lastTimestamp_ =
              items[items.length - 1]['value']['timestamp']['value'];

          if (items.length > MAX_DISPLAYED_NOTIFICATIONS) {
            items = items.slice(-MAX_DISPLAYED_NOTIFICATIONS);
          }

          for (var i = 0; i < items.length; ++i) {
            var item = items[i];

            annotateApiNotification(item);

            this.notify_(
                'GRR', item['value']['message']['value'],
                'GRR' + item['value']['timestamp']['value'], function() {
                  this.grrApiService_.delete(
                      'users/me/notifications/pending/' +
                      item['value']['timestamp']['value']);

                  openReference(item, this.location_);
                }.bind(this));
          }
        }.bind(this));
  }
};



/**
 * Directive that displays desktop notifications.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.UserDesktopNotificationsDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    controller: UserDesktopNotificationsController,
    controllerAs: 'controller'
  };
};

var UserDesktopNotificationsDirective =
    exports.UserDesktopNotificationsDirective;


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
UserDesktopNotificationsDirective.directive_name =
    'grrUserDesktopNotifications';
