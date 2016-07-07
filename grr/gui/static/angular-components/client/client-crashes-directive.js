'use strict';

goog.provide('grrUi.client.clientCrashesDirective.ClientCrashesController');
goog.provide('grrUi.client.clientCrashesDirective.ClientCrashesDirective');

goog.scope(function() {

/**
 * Controller for ClientCrashesDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.clientCrashesDirective.ClientCrashesController = function(
    $scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.clientId;

  /** @type {Array.<Object>} */
  this.crashes;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
};
var ClientCrashesController =
    grrUi.client.clientCrashesDirective.ClientCrashesController;


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new client id.
 * @private
 */
ClientCrashesController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;

  this.grrApiService_.get('clients/' + clientId + '/crashes').then(
      function (response) {
    this.crashes = response['data']['items'];
  }.bind(this));
};

/**
 * ClientCrashesDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.clientCrashesDirective.ClientCrashesDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/client-crashes.html',
    controller: ClientCrashesController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.clientCrashesDirective.ClientCrashesDirective.directive_name =
    'grrClientCrashes';

});  // goog.scope
