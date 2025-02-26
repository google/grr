goog.module('grrUi.flow.flowInfoDirective');



/**
 * Controller for FlowInfoDirective.
 * @unrestricted
 */
const FlowInfoController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;
  }
};


/**
 * FlowInfoDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.FlowInfoDirective = function() {
  return {
    scope: {descriptor: '='},
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
exports.FlowInfoDirective.directive_name = 'grrFlowInfo';
