goog.module('grrUi.client.clientCrashesDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for ClientCrashesDirective.
 * @unrestricted
 */
const ClientCrashesController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrApiService, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!routingService.RoutingService} */
    this.grrRoutingService_ = grrRoutingService;

    /** @type {string} */
    this.clientId;

    /** @type {Array.<Object>} */
    this.crashes;

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, 'clientId', this.onClientIdChange_.bind(this));
  }

  /**
   * Handles changes to the client id state param.
   *
   * @param {string} clientId The new client id.
   * @private
   */
  onClientIdChange_(clientId) {
    this.clientId = clientId;

    this.grrApiService_.get('clients/' + clientId + '/crashes')
        .then(function(response) {
          this.crashes = response['data']['items'];
        }.bind(this));
  }
};



/**
 * ClientCrashesDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.ClientCrashesDirective = function() {
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
exports.ClientCrashesDirective.directive_name = 'grrClientCrashes';
