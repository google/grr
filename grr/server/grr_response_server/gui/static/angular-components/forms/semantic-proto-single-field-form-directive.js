'use strict';

goog.module('grrUi.forms.semanticProtoSingleFieldFormDirective');
goog.module.declareLegacyNamespace();



/**
 * SemanticProtoSingleFieldFormDirective renders a form corresponding to a
 * single (non-repeated) field of a RDFProtoStruct.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticProtoSingleFieldFormDirective = function() {
  return {
    scope: {
      value: '=',
      field: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/' +
        'semantic-proto-single-field-form.html'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticProtoSingleFieldFormDirective.directive_name =
    'grrFormProtoSingleField';
