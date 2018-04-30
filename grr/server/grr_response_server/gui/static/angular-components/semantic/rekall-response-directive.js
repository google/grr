'use strict';

goog.module('grrUi.semantic.rekallResponseDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays RekallResponse values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.RekallResponseDirective = function() {
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
exports.RekallResponseDirective.directive_name = 'grrRekallResponse';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.RekallResponseDirective.semantic_type = 'RekallResponse';
