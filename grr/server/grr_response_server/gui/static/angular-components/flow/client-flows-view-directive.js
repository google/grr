goog.module('grrUi.flow.clientFlowsViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for ClientFlowsViewDirective.
 * @unrestricted
 */
const ClientFlowsViewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!routingService.RoutingService} */
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
  }

  /**
   * Handles changes to the client id state param.
   *
   * @param {Array} unused_newValues The new values for the watched params.
   * @param {Object=} opt_stateParams A dictionary of all state params and their
   *     values.
   * @private
   */
  onRoutingParamsChange_(unused_newValues, opt_stateParams) {
    this.clientId = opt_stateParams['clientId'];
    this.selectedFlowId = opt_stateParams['flowId'];
    this.tab = opt_stateParams['tab'];
    this.flowApiBasePath = ['clients', this.clientId, 'flows'].join('/');
  }

  /**
   * Handles binding changes.
   *
   * @private
   */
  onSelectionOrTabChange_() {
    if (angular.isDefined(this.selectedFlowId)) {
      this.grrRoutingService_.go(
          'client.flows', {flowId: this.selectedFlowId, tab: this.tab});
    }
  }
};



/**
 * FlowsViewDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.ClientFlowsViewDirective = function() {
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
exports.ClientFlowsViewDirective.directive_name = 'grrClientFlowsView';
