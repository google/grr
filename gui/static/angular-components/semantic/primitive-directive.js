'use strict';

goog.provide('grrUi.semantic.primitiveDirective.PrimitiveDirective');

goog.scope(function() {


/**
 * Directive that displays Primitive values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.primitiveDirective.PrimitiveDirective = function() {
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
grrUi.semantic.primitiveDirective.PrimitiveDirective.directive_name =
    'grrPrimitive';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.primitiveDirective.PrimitiveDirective.semantic_types =
    ['RDFBool', 'bool',
     'RDFInteger', 'int', 'long', 'float',
     'RDFString', 'basestring'];


});  // goog.scope
