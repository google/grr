'use strict';

goog.module('grrUi.semantic.apiHuntResultDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays ApiHuntResult values.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ApiHuntResultDirective = function() {
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
exports.ApiHuntResultDirective.directive_name = 'grrApiHuntResult';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ApiHuntResultDirective.semantic_type = 'ApiHuntResult';
