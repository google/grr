'use strict';

goog.module('grrUi.flow.flowStatusIconDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays flow status icons for a given flow.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.FlowStatusIconDirective = function() {
  return {
    scope: {flow: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-status-icon.html'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.FlowStatusIconDirective.directive_name = 'grrFlowStatusIcon';
