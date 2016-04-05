'use strict';

goog.provide('grrUi.flow.flowLogDirective.FlowLogController');
goog.provide('grrUi.flow.flowLogDirective.FlowLogDirective');

goog.scope(function() {


/**
 * Controller for FlowLogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.flowLogDirective.FlowLogController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  this.scope_.$watch('flowUrn', this.onFlowUrnChange.bind(this));
};

var FlowLogController =
    grrUi.flow.flowLogDirective.FlowLogController;


/**
 * Handles flowUrn attribute changes.
 * @export
 */
FlowLogController.prototype.onFlowUrnChange = function() {
  if (angular.isDefined(this.scope_['flowUrn'])) {
    var flowUrnComponents = this.scope_['flowUrn'].split('/');
    var clientId = flowUrnComponents[1];
    var flowId = flowUrnComponents[flowUrnComponents.length - 1];
    this.logsUrl = 'clients/' + clientId + '/flows/' + flowId + "/log";
  }
};


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
      flowUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-log.html',
    controller: FlowLogController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowLogDirective.FlowLogDirective.directive_name = 'grrFlowLog';


});  // goog.scope
