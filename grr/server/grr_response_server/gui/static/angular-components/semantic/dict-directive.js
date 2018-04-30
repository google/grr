'use strict';

goog.module('grrUi.semantic.dictDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays dicts.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.DictDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/dict.html',
  };
};


/**
 * Name of the directive in Angular.
 */
exports.DictDirective.directive_name = 'grrDict';


/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
exports.DictDirective.semantic_types = ['dict', 'Dict'];
