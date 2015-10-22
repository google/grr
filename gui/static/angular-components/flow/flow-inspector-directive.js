'use strict';

goog.provide('grrUi.flow.flowInspectorDirective.FlowInspectorDirective');

goog.scope(function() {



/**
 * FlowInspectorDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.flowInspectorDirective.FlowInspectorDirective = function() {
  return {
    scope: {
      flowUrn: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-inspector.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowInspectorDirective.FlowInspectorDirective
    .directive_name = 'grrFlowInspector';



});  // goog.scope
