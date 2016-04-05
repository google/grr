'use strict';

goog.provide('grrUi.semantic.dictDirective.DictController');
goog.provide('grrUi.semantic.dictDirective.DictDirective');

goog.scope(function() {


/**
 * Directive that displays dicts.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.dictDirective.DictDirective = function() {
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
grrUi.semantic.dictDirective.DictDirective.directive_name =
    'grrDict';


/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.dictDirective.DictDirective.semantic_types =
    ['dict', 'Dict'];


});  // goog.scope
