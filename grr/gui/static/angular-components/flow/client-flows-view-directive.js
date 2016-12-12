'use strict';

goog.provide('grrUi.flow.clientFlowsViewDirective.ClientFlowsViewController');
goog.provide('grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective');

goog.scope(function() {


/**
 * Controller for ClientFlowsViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.flow.clientFlowsViewDirective.ClientFlowsViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.clientId;

  /** @type {string} */
  this.selectedFlowId;

  /** @type {string} */
  this.tab;

  /** @type {string} */
  this.flowApiBasePath;

  this.scope_.$watchGroup(
      ['controller.selectedFlowId', 'controller.tab'],
      this.onSelectionOrTabChange_.bind(this));

  this.grrRoutingService_.uiOnParamsChanged(
      this.scope_, ['clientId', 'flowId', 'tab'],
      this.onRoutingParamsChange_.bind(this));
};
var ClientFlowsViewController =
    grrUi.flow.clientFlowsViewDirective.ClientFlowsViewController;


/**
 * Handles changes to the client id state param.
 *
 * @param {Array} unused_newValues The new values for the watched params.
 * @param {Object=} opt_stateParams A dictionary of all state params and their values.
 * @private
 */
ClientFlowsViewController.prototype.onRoutingParamsChange_ = function(
    unused_newValues, opt_stateParams) {
  this.clientId = opt_stateParams['clientId'];
  this.selectedFlowId = opt_stateParams['flowId'];
  this.tab = opt_stateParams['tab'];
  this.flowApiBasePath = ['clients', this.clientId, 'flows'].join('/');
};

/**
 * Handles selectedFlowUrn binding changes.
 *
 * @private
 */
ClientFlowsViewController.prototype.onSelectionOrTabChange_ = function() {
  if (angular.isDefined(this.selectedFlowId)) {
    this.grrRoutingService_.go('client.flows',
                               {flowId: this.selectedFlowId, tab: this.tab});
  }
};

/**
 * FlowsViewDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/client-flows-view.html',
    controller: ClientFlowsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective
    .directive_name = 'grrClientFlowsView';



});  // goog.scope
