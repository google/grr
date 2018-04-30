'use strict';

goog.module('grrUi.client.clientLoadViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ClientLoadViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
const ClientLoadViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.cliendId;

  /** @export {number} Queries start time. */
  this.startTime;

  /** @export {number} Queries end time. */
  this.endTime;

  /** @export {number} Max duration of graphs to show (in minutes). */
  this.duration = 60;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
                                            this.onClientIdChange_.bind(this));

  this.scope_.$watch('controller.duration', this.onDurationChange.bind(this));
};


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
 * Handles changes of 'controller.duration' value.
 *
 * @param {number} newValue New duration value.
 * @export
 */
ClientLoadViewController.prototype.onDurationChange = function(newValue) {
  this.endTime = Math.round(new Date().getTime() * 1000);
  this.startTime = this.endTime - this.duration * 60 * 1000000;
};


/**
 * ClientLoadViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.ClientLoadViewDirective = function() {
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
exports.ClientLoadViewDirective.directive_name = 'grrClientLoadView';
