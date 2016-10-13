'use strict';

goog.provide('grrUi.config.configBinariesViewDirective.ConfigBinariesViewController');
goog.provide('grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective');

goog.scope(function() {


/**
 * Controller for ConfigBinariesViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.config.configBinariesViewDirective.ConfigBinariesViewController = function(
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
var ConfigBinariesViewController =
    grrUi.config.configBinariesViewDirective.ConfigBinariesViewController;


/**
 * ConfigBinariesViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective =
    function() {
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
grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective
    .directive_name = 'grrConfigBinariesView';

});  // goog.scope
