'use strict';

goog.provide('grrUi.docs.apiDescriptionDirective.ApiDescriptionController');
goog.provide('grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective');

goog.scope(function() {



/**
 * Cotnroller for ApiDescriptionDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.docs.apiDescriptionDirective.ApiDescriptionController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {!Array.<string>} */
  this.paragraphs = [];

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};
var ApiDescriptionController =
    grrUi.docs.apiDescriptionDirective.ApiDescriptionController;


/**
 * Handles value attribute changes.
 *
 * @param {string} newValue New route value.
 * @export
 */
ApiDescriptionController.prototype.onValueChange = function(newValue) {
  if (angular.isString(newValue)) {
    this.paragraphs = newValue.split('\n\n');
  }
};



/**
 * Directive for displaying API route.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/docs/api-description.html',
    controller: ApiDescriptionController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective.directive_name =
    'grrApiDescription';




});  // goog.scope
