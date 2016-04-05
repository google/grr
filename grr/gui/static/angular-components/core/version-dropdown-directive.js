'use strict';

goog.provide('grrUi.core.versionDropdownDirective.VersionDropdownController');
goog.provide('grrUi.core.versionDropdownDirective.VersionDropdownDirective');


goog.scope(function() {


/**
 * Controller for VersionDropdownDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.core.versionDropdownDirective.VersionDropdownController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array} */
  this.versions;

  this.scope_.$watch('url', this.onDirectiveArgumentsChange_.bind(this));
};

var VersionDropdownController =
    grrUi.core.versionDropdownDirective.VersionDropdownController;


/**
 * Handles changes of clientId binding.
 *
 * @private
 */
VersionDropdownController.prototype.onDirectiveArgumentsChange_ = function() {
  var url = this.scope_['url'];
  var responseField = this.scope_['responseField'] || 'times';

  if (angular.isDefined(url)) {
    this.grrApiService_.get(url).then(function(response) {
      this.versions = response['data'][responseField];
    }.bind(this));
  }
};


/**
 * VersionDropdownDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.core.versionDropdownDirective.VersionDropdownDirective = function() {
  return {
    restrict: 'E',
    scope: {
      url: '=',
      version: '=',
      responseField: '@'
    },
    templateUrl: '/static/angular-components/core/version-dropdown.html',
    controller: VersionDropdownController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.core.versionDropdownDirective.VersionDropdownDirective.directive_name =
    'grrVersionDropdown';

});  // goog.scope
