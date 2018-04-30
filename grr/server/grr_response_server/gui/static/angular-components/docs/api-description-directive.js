'use strict';

goog.module('grrUi.docs.apiDescriptionDirective');
goog.module.declareLegacyNamespace();



/**
 * Cotnroller for ApiDescriptionDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ApiDescriptionController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {!Array.<string>} */
  this.paragraphs = [];

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};


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
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ApiDescriptionDirective = function() {
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
exports.ApiDescriptionDirective.directive_name = 'grrApiDescription';
