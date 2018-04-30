'use strict';

goog.module('grrUi.docs.apiQuerySpecDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ApiQuerySpecDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
const ApiQuerySpecController = function(
    $scope, grrReflectionService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @export {Array.<Object>} */
  this.descriptorFields;

  /** @export {Object.<string, Object>} */
  this.descriptorsCache;

  /** @export {Object.<string, string>} */
  this.typeHints = {
    'RDFDatetime': 'Time since epoch in microseconds.',
    'RDFBool': 'Either 1 or 0.',
    'RDFURN': 'Path string with components separated by "/", i.e. ' +
        '"foo/bar/blah".'
  };

  this.scope_.$watch('argsType', this.onArgsTypeChange.bind(this));
};



/**
 * Handles value attribute changes.
 *
 * @param {string} newValue New args type value.
 * @export
 */
ApiQuerySpecController.prototype.onArgsTypeChange = function(newValue) {
  this.argsDescriptor = null;
  if (angular.isString(newValue)) {
    this.grrReflectionService_.getRDFValueDescriptor(newValue, true).then(
        function(result) {
          this.descriptorFields = [];
          angular.forEach(result[newValue]['fields'], function(field) {
            if (field.name !== 'additional_args') {
              this.descriptorFields.push(field);
            }
          }.bind(this));

          this.descriptorsCache = result;
        }.bind(this));
  }
};



/**
 * Directive for displaying API query specificiation.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ApiQuerySpecDirective = function() {
  return {
    scope: {
      argsType: '=',
      prefix: '=',
      noHeader: '@'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/docs/api-query-spec.html',
    controller: ApiQuerySpecController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ApiQuerySpecDirective.directive_name = 'grrApiQuerySpec';
