'use strict';

goog.module('grrUi.config.configBinariesViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ConfigBinariesViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const ConfigBinariesViewController = function(
    $scope, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array<Object>|undefined} */
  this.binaries;

  this.grrApiService_.get('/config/binaries').then(function(response) {
    this.binaries = response['data']['items'];
  }.bind(this));
};


/**
 * ConfigBinariesViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.ConfigBinariesViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/config/config-binaries-view.html',
    controller: ConfigBinariesViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ConfigBinariesViewDirective.directive_name = 'grrConfigBinariesView';
