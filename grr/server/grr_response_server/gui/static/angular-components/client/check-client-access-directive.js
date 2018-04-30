'use strict';

goog.module('grrUi.client.checkClientAccessDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for CheckClientAccessDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$timeout} $timeout
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
const CheckClientAccessController = function(
    $scope, $timeout, grrApiService, grrRoutingService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$timeout} */
  this.timeout_ = $timeout;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  this.scope_.$watch('clientId', this.onClientIdChange_.bind(this));
};



/**
 * Handles changes to the client id.
 *
 * @param {string} clientId The new value for the client id state param.
 * @private
 */
CheckClientAccessController.prototype.onClientIdChange_ = function(clientId) {
  if (angular.isDefined(clientId)) {
    this.scope_['outHasAccess'] = undefined;

    this.grrApiService_.head('clients/' + clientId + '/flows').then(
        this.onClientAccessPermitted_.bind(this),
        this.onClientAccessRejected_.bind(this));
  }
};


/**
 * @private
 */
CheckClientAccessController.prototype.onClientAccessPermitted_ = function() {
  this.scope_['outHasAccess'] = true;
};

/**
 * @private
 */
CheckClientAccessController.prototype.onClientAccessRejected_ = function() {
  this.scope_['outHasAccess'] = false;

  if (!this.scope_['noRedirect']) {
    this.timeout_(function() {
      var clientId = this.scope_['clientId'];
      if (angular.isDefined(clientId)) {
        this.grrRoutingService_.go('client', {
          clientId: clientId
        });
      }
    }.bind(this), 1000);
  }
};



/**
 * Directive that displays data objects.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.CheckClientAccessDirective = function() {
  return {
    scope: {
      noRedirect: '=',
      clientId: '=',
      outHasAccess: '=?' // hasAccess is an "out" binding, and not a simple
                         // parameter. Other directives may bind to hasAccess to
                         // check whether access to the client is allowed.
    },
    transclude: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/client/check-client-access.html',
    controller: CheckClientAccessController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.CheckClientAccessDirective.directive_name = 'grrCheckClientAccess';
