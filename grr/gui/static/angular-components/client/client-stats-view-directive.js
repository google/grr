'use strict';

goog.provide('grrUi.client.clientStatsViewDirective.ClientStatsViewController');
goog.provide('grrUi.client.clientStatsViewDirective.ClientStatsViewDirective');

goog.scope(function() {

/**
 * Controller for ClientStatsViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.clientStatsViewDirective.ClientStatsViewController = function(
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
var ClientStatsViewController =
    grrUi.client.clientStatsViewDirective.ClientStatsViewController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new client id.
 * @private
 */
ClientStatsViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
};

/**
 * ClientStatsViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.clientStatsViewDirective.ClientStatsViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/client-stats-view.html',
    controller: ClientStatsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.clientStatsViewDirective.ClientStatsViewDirective.directive_name =
    'grrClientStatsView';

});  // goog.scope
