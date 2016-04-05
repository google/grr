'use strict';

goog.provide('grrUi.flow.flowInfoDirective.FlowInfoController');
goog.provide('grrUi.flow.flowInfoDirective.FlowInfoDirective');

goog.scope(function() {

/**
 * Controller for FlowInfoDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.flowInfoDirective.FlowInfoController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;
};
var FlowInfoController = grrUi.flow.flowInfoDirective.FlowInfoController;


/**
 * FlowInfoDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.flowInfoDirective.FlowInfoDirective = function() {
  return {
    scope: {
      descriptor: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-info.html',
    controller: FlowInfoController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowInfoDirective.FlowInfoDirective.directive_name =
    'grrFlowInfo';



});  // goog.scope
