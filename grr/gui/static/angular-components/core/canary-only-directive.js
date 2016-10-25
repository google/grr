'use strict';

goog.provide('grrUi.core.canaryOnlyDirective.CanaryOnlyController');
goog.provide('grrUi.core.canaryOnlyDirective.CanaryOnlyDirective');
goog.provide('grrUi.core.canaryOnlyDirective.NonCanaryOnlyController');
goog.provide('grrUi.core.canaryOnlyDirective.NonCanaryOnlyDirective');


goog.scope(function() {


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
grrUi.core.canaryOnlyDirective.CanaryOnlyDirective = function() {
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
grrUi.core.canaryOnlyDirective.CanaryOnlyDirective
    .directive_name = 'grrCanaryOnly';


/**
 * Directive that renders its contents only in nonCanary mode.
 *
 * @constructor
 * @ngInject
 * @export
 * @return {angular.Directive} Directive definition object.
 */
grrUi.core.canaryOnlyDirective.NonCanaryOnlyDirective = function() {
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
grrUi.core.canaryOnlyDirective.NonCanaryOnlyDirective
    .directive_name = 'grrNonCanaryOnly';


});  // goog.scope
