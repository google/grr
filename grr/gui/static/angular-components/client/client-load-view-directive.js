'use strict';

goog.provide('grrUi.client.clientLoadViewDirective.ClientLoadViewController');
goog.provide('grrUi.client.clientLoadViewDirective.ClientLoadViewDirective');

goog.scope(function() {

/**
 * Controller for ClientLoadViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.clientLoadViewDirective.ClientLoadViewController = function(
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
var ClientLoadViewController =
    grrUi.client.clientLoadViewDirective.ClientLoadViewController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new client id.
 * @private
 */
ClientLoadViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
};

/**
 * ClientLoadViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.clientLoadViewDirective.ClientLoadViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/client-load-view.html',
    controller: ClientLoadViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.clientLoadViewDirective.ClientLoadViewDirective.directive_name =
    'grrClientLoadView';

});  // goog.scope
