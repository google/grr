'use strict';

goog.provide('grrUi.client.virtualFileSystem.encodingsDropdownDirective.EncodingsDropdownController');
goog.provide('grrUi.client.virtualFileSystem.encodingsDropdownDirective.EncodingsDropdownDirective');


goog.scope(function() {


/**
 * Controller for EncodingsDropdownDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.encodingsDropdownDirective.EncodingsDropdownController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.grrApiService_.get('reflection/file-encodings').then(function(response){
    this.encodings = response.data['encodings'];
  }.bind(this));
};

var EncodingsDropdownController =
    grrUi.client.virtualFileSystem.encodingsDropdownDirective.EncodingsDropdownController;


/**
 * EncodingsDropdownDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.encodingsDropdownDirective.EncodingsDropdownDirective = function() {
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
grrUi.client.virtualFileSystem.encodingsDropdownDirective.EncodingsDropdownDirective.directive_name =
    'grrEncodingsDropdown';

});  // goog.scope
