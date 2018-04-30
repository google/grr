'use strict';

goog.module('grrUi.core.canaryOnlyDirective');
goog.module.declareLegacyNamespace();

const {ApiService} = goog.require('grrUi.core.apiService');


/**
 * Determines whether the canary mode is on.
 *
 * @param {!ApiService} grrApiService
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
 * @constructor
 * @param {!ApiService} grrApiService
 * @ngInject
 */
const CanaryOnlyController = function(grrApiService) {
  /** @type {boolean} */
  // Hide the contents until the api call returns.
  this.canaryMode = false;

  getCanaryModeValue(grrApiService, (canaryMode) => {
    this.canaryMode = canaryMode;
  });
};

/**
 * @constructor
 * @param {!ApiService} grrApiService
 * @ngInject
 */
const NonCanaryOnlyController = function(grrApiService) {
  /** @type {boolean} */
  // Hide the contents until the api call returns.
  this.canaryMode = true;

  getCanaryModeValue(grrApiService, (canaryMode) => {
    this.canaryMode = canaryMode;
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
    controller: CanaryOnlyController,
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
    controller: NonCanaryOnlyController,
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
