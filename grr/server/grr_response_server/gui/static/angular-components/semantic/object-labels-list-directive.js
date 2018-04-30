'use strict';

goog.module('grrUi.semantic.objectLabelsListDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays AFF4 object labels list.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ObjectLabelsListDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    template: '<grr-object-label ' +
        'ng-repeat="label in ::value.value.labels" ' +
        'value="::label"></grr-object-label>',
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.ObjectLabelsListDirective.directive_name = 'grrObjectLabelsList';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ObjectLabelsListDirective.semantic_type = 'AFF4ObjectLabelsList';
