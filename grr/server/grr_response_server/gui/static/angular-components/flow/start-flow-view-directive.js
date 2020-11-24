goog.module('grrUi.flow.startFlowViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for StartFlowViewDirective.
 * @unrestricted
 */
const StartFlowViewController = class {
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
    this.cliendId;

    /** @type {Object} */
    this.selection = {};

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, 'clientId', this.onClientIdChange_.bind(this));
  }

  /**
   * Handles changes to the client id state param.
   *
   * @param {string} clientId The new value for the client id.
   * @private
   */
  onClientIdChange_(clientId) {
    this.clientId = clientId;
  }
};



/**
 * StartFlowViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.StartFlowViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/start-flow-view.html',
    controller: StartFlowViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.StartFlowViewDirective.directive_name = 'grrStartFlowView';
