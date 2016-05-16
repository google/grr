'use strict';

goog.provide('grrUi.client.debugRequestsViewDirective.DebugRequestsViewController');
goog.provide('grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective');

goog.scope(function() {

/**
 * Controller for DebugRequestsViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.debugRequestsViewDirective.DebugRequestsViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.cliendId;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
};
var DebugRequestsViewController =
    grrUi.client.debugRequestsViewDirective.DebugRequestsViewController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new client id.
 * @private
 */
DebugRequestsViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
};

/**
 * DebugRequestsViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/debug-requests-view.html',
    controller: DebugRequestsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective.directive_name =
    'grrDebugRequestsView';

});  // goog.scope
