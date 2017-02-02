'use strict';

goog.provide('grrUi.semantic.apiHuntResultDirective.ApiHuntResultDirective');

goog.scope(function() {


/**
 * Directive that displays ApiHuntResult values.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.semantic.apiHuntResultDirective.ApiHuntResultDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/api-hunt-result.html'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.apiHuntResultDirective.ApiHuntResultDirective.directive_name =
    'grrApiHuntResult';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.apiHuntResultDirective.ApiHuntResultDirective.semantic_type =
    'ApiHuntResult';


});  // goog.scope
