'use strict';

goog.provide('grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective');


goog.scope(function() {


/**
 * Directive that displays AFF4 object labels list.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective =
    function() {
      return {
        scope: {
          value: '='
        },
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
grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective
    .directive_name = 'grrObjectLabelsList';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.objectLabelsListDirective
    .ObjectLabelsListDirective.semantic_type =
    'AFF4ObjectLabelsList';


});  // goog.scope
