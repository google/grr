'use strict';

goog.module('grrUi.semantic.dataObjectDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays data objects.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.DataObjectDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/data-object.html',
  };
};


/**
 * Name of the directive in Angular.
 */
exports.DataObjectDirective.directive_name = 'grrDataObject';


/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
exports.DataObjectDirective.semantic_type = 'ApiDataObject';
