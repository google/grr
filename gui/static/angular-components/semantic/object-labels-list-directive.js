'use strict';

goog.provide('grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');


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

grrUi.semantic.SemanticDirectivesRegistry.registerDirective(
    'AFF4ObjectLabelsList',
    grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective);


});  // goog.scope
