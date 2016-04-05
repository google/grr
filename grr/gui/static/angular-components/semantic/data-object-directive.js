'use strict';

goog.provide('grrUi.semantic.dataObjectDirective.DataObjectController');
goog.provide('grrUi.semantic.dataObjectDirective.DataObjectDirective');

goog.scope(function() {


/**
 * Directive that displays data objects.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.dataObjectDirective.DataObjectDirective = function() {
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
grrUi.semantic.dataObjectDirective.DataObjectDirective.directive_name =
    'grrDataObject';


/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.dataObjectDirective.DataObjectDirective.semantic_type =
    'ApiDataObject';


});  // goog.scope
