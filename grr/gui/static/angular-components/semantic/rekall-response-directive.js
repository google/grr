'use strict';

goog.provide('grrUi.semantic.rekallResponseDirective.RekallResponseController');
goog.provide('grrUi.semantic.rekallResponseDirective.RekallResponseDirective');

goog.scope(function() {


/**
 * Directive that displays RekallResponse values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekallResponseDirective.RekallResponseDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/rekall-response.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.rekallResponseDirective.RekallResponseDirective.directive_name =
    'grrRekallResponse';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.rekallResponseDirective.RekallResponseDirective.semantic_type =
    'RekallResponse';


});  // goog.scope
