'use strict';

goog.provide('grrUi.flow.startFlowViewDirective.StartFlowViewDirective');

goog.scope(function() {


/**
 * StartFlowViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.startFlowViewDirective.StartFlowViewDirective = function() {
  return {
    restrict: 'E',
    scope: {
      flowType: '=',
      clientId: '='
    },
    templateUrl: '/static/angular-components/flow/start-flow-view.html',
    link: function(scope) {
      scope.selection = {};
    }
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.startFlowViewDirective.StartFlowViewDirective.directive_name =
    'grrStartFlowView';

});  // goog.scope
