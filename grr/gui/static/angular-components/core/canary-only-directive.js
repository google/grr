'use strict';

goog.module('grrUi.core.canaryOnlyDirective');
goog.module.declareLegacyNamespace();



/**
 * Determines whether the canary mode is on.
 *
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {function(boolean)} callback The canary mode flag will be passed to
 * this callback when it'll be determined in background.
 */
var getCanaryModeValue = function(grrApiService, callback) {
  grrApiService.getCached('/users/me').then(function(response) {
    var canaryMode;

    try {
      canaryMode = /** @type {boolean} */ (
          response['data']['value']['settings']
                  ['value']['canary_mode']['value']);
    } catch(err) {
      canaryMode = false;
    }

    callback(canaryMode);
  });
};


/**
 * Directive that renders its contents only in canary mode.
 *
 * @constructor
 * @ngInject
 * @export
 * @return {angular.Directive} Directive definition object.
 */
exports.CanaryOnlyDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    controller: function(grrApiService) {
      /** @type {boolean} */
      // Hide the contents until the api call returns.
      this.canaryMode = false;

      getCanaryModeValue(grrApiService, function(canaryMode) {
          this.canaryMode = canaryMode;
      }.bind(this));
    },
    controllerAs: 'controller',
    transclude: true,
    template: '<ng-transclude ng-if=\'controller.canaryMode\'></ng-transclude>'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CanaryOnlyDirective.directive_name = 'grrCanaryOnly';


/**
 * Directive that renders its contents only in nonCanary mode.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.NonCanaryOnlyDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    controller: function(grrApiService) {
      /** @type {boolean} */
      // Hide the contents until the api call returns.
      this.canaryMode = true;

      getCanaryModeValue(grrApiService, function(canaryMode) {
          this.canaryMode = canaryMode;
      }.bind(this));
    },
    controllerAs: 'controller',
    transclude: true,
    template: '<ng-transclude ng-if=\'!controller.canaryMode\'></ng-transclude>'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.NonCanaryOnlyDirective.directive_name = 'grrNonCanaryOnly';
