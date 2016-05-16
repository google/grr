'use strict';

goog.provide('grrUi.flow.startFlowViewDirective.StartFlowViewController');
goog.provide('grrUi.flow.startFlowViewDirective.StartFlowViewDirective');

goog.scope(function() {


/**
 * Controller for StartFlowViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.flow.startFlowViewDirective.StartFlowViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.cliendId;

  /** @type {string} */
  this.flowType;

  /** @type {Object} */
  this.selection = {};

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
};
var StartFlowViewController =
    grrUi.flow.startFlowViewDirective.StartFlowViewController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new value for the client id.
 * @private
 */
StartFlowViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
  this.flowType = clientId ? 'CLIENT' : 'GLOBAL';
};


/**
 * StartFlowViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.startFlowViewDirective.StartFlowViewDirective = function() {
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
grrUi.flow.startFlowViewDirective.StartFlowViewDirective.directive_name =
    'grrStartFlowView';

});  // goog.scope
