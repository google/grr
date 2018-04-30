'use strict';

goog.module('grrUi.client.debugRequestsViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for DebugRequestsViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
const DebugRequestsViewController = function(
    $scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.cliendId;

  /** @type {Array<Object>|undefined} */
  this.actionRequests;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
};


/**
 * Handles changes to the client id state param.
 *
 * @param {string} clientId The new client id.
 * @private
 */
DebugRequestsViewController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
  this.actionRequests = undefined;

  if (angular.isDefined(this.clientId)) {
    var url = 'clients/' + this.clientId + '/action-requests';
    var fetchResponses = 1;
    if (angular.isDefined(this.scope_['fetchResponses'])) {
      fetchResponses = this.scope_['fetchResponses'];
    }
    this.grrApiService_.get(
        url, {'fetch_responses': fetchResponses}).then(
            function(response) {
              this.actionRequests = response['data']['items'] || [];
            }.bind(this));
  }
};

/**
 * DebugRequestsViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.DebugRequestsViewDirective = function() {
  return {
    scope: {
      fetchResponses: '='
    },
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
exports.DebugRequestsViewDirective.directive_name = 'grrDebugRequestsView';
