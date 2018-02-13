'use strict';

goog.module('grrUi.semantic.primitiveDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays Primitive values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.PrimitiveDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '{$ ::value.value $}'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.PrimitiveDirective.directive_name = 'grrPrimitive';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.PrimitiveDirective.semantic_types = [
  'RDFBool', 'bool', 'RDFInteger', 'int', 'long', 'float', 'RDFString',
  'basestring'
];
