'use strict';

goog.provide('grrUi.flow.flowLogDirective.FlowLogDirective');

goog.scope(function() {



/**
 * Directive for displaying logs of a flow with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.flow.flowLogDirective.FlowLogDirective = function() {
  return {
    scope: {
      flowUrn: '@'
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/flow/flow-log.html',
    link: function(scope, element) {
      scope.$watch('flowUrn', function() {
        scope.logsUrn = scope.flowUrn + '/Logs';
      });
    }
  };
};


/**
 * Directive's name in Angular.
 */
grrUi.flow.flowLogDirective.FlowLogDirective.directive_name = 'grrFlowLog';

});  // goog.scope
