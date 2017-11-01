'use strict';

goog.provide('grrUi.semantic.huntIdDirective.HuntIdController');
goog.provide('grrUi.semantic.huntIdDirective.HuntIdDirective');

goog.scope(function() {


/**
 * Directive that displays ApiHuntId values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @export
 */
grrUi.semantic.huntIdDirective.HuntIdDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/hunt-id.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.huntIdDirective.HuntIdDirective.directive_name =
    'grrHuntId';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.huntIdDirective.HuntIdDirective.semantic_type =
    'ApiHuntId';


});  // goog.scope
