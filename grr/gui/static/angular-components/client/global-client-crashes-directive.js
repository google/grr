'use strict';

goog.provide('grrUi.client.globalClientCrashesDirective.GlobalClientCrashesController');
goog.provide('grrUi.client.globalClientCrashesDirective.GlobalClientCrashesDirective');

goog.scope(function() {

/**
 * Controller for GlobalClientCrashesDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.globalClientCrashesDirective.GlobalClientCrashesController = function(
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
var GlobalClientCrashesController =
    grrUi.client.globalClientCrashesDirective.GlobalClientCrashesController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new client id.
 * @private
 */
GlobalClientCrashesController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
};

/**
 * GlobalClientCrashesDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.globalClientCrashesDirective.GlobalClientCrashesDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/global-client-crashes.html',
    controller: GlobalClientCrashesController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.globalClientCrashesDirective.GlobalClientCrashesDirective.directive_name =
    'grrGlobalClientCrashes';

});  // goog.scope
