'use strict';

goog.provide('grrUi.client.clientStatusIconsDirective.ClientStatusIconsController');
goog.provide('grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective');


goog.scope(function() {


/**
 * Controller for ClientStatusIconsDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @constructor
 * @ngInject
 */
grrUi.client.clientStatusIconsDirective.ClientStatusIconsController = function(
    $scope, grrTimeService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.timeService.TimeService} */
  this.grrTimeService_ = grrTimeService;

  /** @export {?string} */
  this.iconName;

  /** @export {?number} */
  this.crashTime;

  /** @export {Array<Object>} */
  this.diskWarnings = [];

  /** @export {?number} */
  this.lastPing;

  this.scope_.$watch('::client', this.onClientChange_.bind(this));
};
var ClientStatusIconsController =
    grrUi.client.clientStatusIconsDirective.ClientStatusIconsController;


/**
 * Handles changes of scope.client attribute.
 *
 * @param {number} newValue Client object (with types or without)
 * @private
 */
ClientStatusIconsController.prototype.onClientChange_ = function(newValue) {
  this.iconName = this.showCrashIcon = null;
  this.diskWarnings = [];

  if (angular.isObject(newValue)) {
    this.lastPing = /** @type {number} */ (this.scope_.$eval(
        'client.value.last_seen_at.value'));
    if (angular.isUndefined(this.lastPing)) {
      this.lastPing = 0;
    }

    var currentTimeMs = this.grrTimeService_.getCurrentTimeMs();
    var timeLastSeenSecs = (currentTimeMs - this.lastPing / 1000) / 1000;

    if (timeLastSeenSecs < 60 * 15) {
      this.iconName = 'online';
    } else if (timeLastSeenSecs < 60 * 60 * 24) {
      this.iconName = 'online-1d';
    } else {
      this.iconName = 'offline';
    }

    var crashTime = /** @type {number} */ (this.scope_.$eval(
        'client.value.last_crash_at.value'));
    if (angular.isDefined(crashTime) &&
        (currentTimeMs / 1000 - crashTime / 1000000) < 60 * 60 * 24) {
      this.crashTime = crashTime;
    }

    angular.forEach(newValue['value']['volumes'] || [], function(volume) {
      if (volume['value']['windowsvolume'] &&
          volume['value']['windowsvolume']['value']['drive_type']['value'] ==
          'DRIVE_CDROM') {
        return;
      }

      if (angular.isDefined(volume['value']
                            ['actual_available_allocation_units']) &&
          angular.isDefined(volume['value']['total_allocation_units'])) {
        var percent = (
            volume['value']['actual_available_allocation_units']['value'] /
                volume['value']['total_allocation_units']['value']) * 100;
        if (percent <= 5) {
          var volumeName = '';
          if (volume['value']['name']) {
            volumeName = volume['value']['name']['value'];
          }
          this.diskWarnings.push([volumeName, percent]);
        }
      }
    }.bind(this));
  }
};


/**
 * Directive that displays client status icons for a given client.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective =
    function() {
      return {
        scope: {
          client: '='
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/client/' +
            'client-status-icons.html',
        controller: ClientStatusIconsController,
        controllerAs: 'controller'
      };
    };


/**
 * Name of the directive in Angular.
 */
grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective
    .directive_name = 'grrClientStatusIcons';


});  // goog.scope
