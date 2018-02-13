'use strict';

goog.module('grrUi.flow.startFlowViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for StartFlowViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
const StartFlowViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.cliendId;

  /** @type {Object} */
  this.selection = {};

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
};


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new value for the client id.
 * @private
 */
StartFlowViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
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
