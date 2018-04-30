'use strict';

goog.module('grrUi.client.virtualFileSystem.encodingsDropdownDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for EncodingsDropdownDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const EncodingsDropdownController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.grrApiService_.get('reflection/file-encodings').then(function(response){
    this.encodings = response.data['encodings'];
  }.bind(this));
};



/**
 * EncodingsDropdownDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.EncodingsDropdownDirective = function() {
  return {
    restrict: 'E',
    scope: {
      encoding: '=',
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/encodings-dropdown.html',
    controller: EncodingsDropdownController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.EncodingsDropdownDirective.directive_name = 'grrEncodingsDropdown';
