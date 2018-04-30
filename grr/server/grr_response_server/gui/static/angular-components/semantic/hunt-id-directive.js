'use strict';

goog.module('grrUi.semantic.huntIdDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays ApiHuntId values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @export
 */
exports.HuntIdDirective = function() {
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
exports.HuntIdDirective.directive_name = 'grrHuntId';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.HuntIdDirective.semantic_type = 'ApiHuntId';
