'use strict';

goog.provide('grrUi.hunt.huntCrashesDirective');
goog.provide('grrUi.hunt.huntCrashesDirective.HuntCrashesDirective');

goog.scope(function() {


/** @const {number} */
grrUi.hunt.huntCrashesDirective.AUTO_REFRESH_INTERVAL_MS = 20 * 1000;


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
  this.autoRefreshInterval =
      grrUi.hunt.huntCrashesDirective.AUTO_REFRESH_INTERVAL_MS;

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
grrUi.hunt.huntCrashesDirective.HuntCrashesDirective = function() {
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
grrUi.hunt.huntCrashesDirective.HuntCrashesDirective.directive_name =
    'grrHuntCrashes';

});  // goog.scope
