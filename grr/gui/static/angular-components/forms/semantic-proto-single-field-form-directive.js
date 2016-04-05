'use strict';

goog.provide('grrUi.forms.semanticProtoSingleFieldFormDirective.SemanticProtoSingleFieldFormController');
goog.provide('grrUi.forms.semanticProtoSingleFieldFormDirective.SemanticProtoSingleFieldFormDirective');


/**
 * SemanticProtoSingleFieldFormDirective renders a form corresponding to a
 * single (non-repeated) field of a RDFProtoStruct.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticProtoSingleFieldFormDirective
    .SemanticProtoSingleFieldFormDirective = function() {
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
grrUi.forms.semanticProtoSingleFieldFormDirective
    .SemanticProtoSingleFieldFormDirective.directive_name =
    'grrFormProtoSingleField';
