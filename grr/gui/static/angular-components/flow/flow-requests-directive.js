'use strict';

goog.provide('grrUi.flow.flowRequestsDirective.FlowRequestsController');
goog.provide('grrUi.flow.flowRequestsDirective.FlowRequestsDirective');

goog.scope(function() {


/**
 * Controller for FlowRequestsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.flowRequestsDirective.FlowRequestsController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.requestsUrl;

  this.scope_.$watch('flowUrn', this.onFlowUrnChange.bind(this));
};

var FlowRequestsController =
    grrUi.flow.flowRequestsDirective.FlowRequestsController;


/**
 * Handles flowUrn attribute changes.
 *
 * @param {string} newFlowUrn
 * @export
 */
FlowRequestsController.prototype.onFlowUrnChange = function(newFlowUrn) {
  if (angular.isDefined(newFlowUrn)) {
    var flowUrnComponents = newFlowUrn.split('/');
    var clientId = flowUrnComponents[1];
    var flowId = flowUrnComponents[flowUrnComponents.length - 1];
    this.requestsUrl = 'clients/' + clientId + '/flows/' + flowId + "/requests";
  }
};


/**
 * Directive for displaying requests of a flow with a given URN.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.flow.flowRequestsDirective.FlowRequestsDirective = function() {
  return {
    scope: {
      flowUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-requests.html',
    controller: FlowRequestsController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowRequestsDirective.FlowRequestsDirective
    .directive_name = 'grrFlowRequests';


});  // goog.scope
