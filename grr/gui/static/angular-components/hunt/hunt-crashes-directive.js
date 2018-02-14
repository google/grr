'use strict';

goog.module('grrUi.hunt.huntCrashesDirective');
goog.module.declareLegacyNamespace();



/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 20 * 1000;

/**
 * Sets the delay between automatic refreshes.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/**
 * Controller for HuntCrashesDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const HuntCrashesController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntId;

  /** @export {string} */
  this.crashesUrl;

  /** @type {number} */
  this.autoRefreshInterval = AUTO_REFRESH_INTERVAL_MS;

  this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
};



/**
 * Handles huntId attribute changes.
 *
 * @param {string} huntId
 * @private
 */
HuntCrashesController.prototype.onHuntIdChange_ = function(huntId) {
  if (angular.isDefined(huntId)) {
    this.crashesUrl = 'hunts/' + huntId + '/crashes';
  }
};


/**
 * Directive for displaying crashes of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntCrashesDirective = function() {
  return {
    scope: {
      huntId: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-crashes.html',
    controller: HuntCrashesController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntCrashesDirective.directive_name = 'grrHuntCrashes';
