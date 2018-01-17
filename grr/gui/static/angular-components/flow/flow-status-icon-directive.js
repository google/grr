'use strict';

goog.provide('grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective');


goog.scope(function() {


/**
 * Directive that displays flow status icons for a given flow.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective =
    function() {
      return {
        scope: {
          flow: '='
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/flow/flow-status-icon.html'
      };
    };


/**
 * Name of the directive in Angular.
 */
grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective
    .directive_name = 'grrFlowStatusIcon';
});  // goog.scope
