'use strict';

goog.provide('grrUi.sidebar.navigatorDirective.NavigatorController');
goog.provide('grrUi.sidebar.navigatorDirective.NavigatorDirective');
goog.require('grrUi.core.apiService.stripTypeInfo');


goog.scope(function() {


var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;


/**
 * Controller for NavigatorDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.sidebar.navigatorDirective.NavigatorController = function(
    $scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {Object} */
  this.client;

  /** @type {?string} */
  this.clientId;

  /** @type {boolean} */
  this.hasClientAccess = false;

  /** @type {Object} */
  this.uiTraits;

  // Fetch UI traits.
  this.grrApiService_.getCached('users/me').then(function (response) {
    this.uiTraits = stripTypeInfo(response['data'])['interface_traits'];
  }.bind(this));

  // Subscribe to legacy grr events to be notified on client change.
  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientSelectionChange_.bind(this), true);
};

var NavigatorController =
    grrUi.sidebar.navigatorDirective.NavigatorController;


/**
 * Handles selection of a client.
 *
 * @param {string} clientId The id of the selected client.
 * @private
 */
NavigatorController.prototype.onClientSelectionChange_ = function(clientId) {
  if (!clientId) {
    return; // Stil display the last client for convenience.
  }
  if (clientId.indexOf('aff4:/') === 0) {
    clientId = clientId.split('/')[1];
  }
  if (this.clientId === clientId) {
    return;
  }

  // Keep to not break integration with the legacy JS code. Remove once the
  // legacy JS plugins are removed.
  if (!grr.state) {
    grr.state = {
      client_id: 'aff4:/' + clientId
    };
  } else {
    grr.state.client_id = 'aff4:/' + clientId;
  }

  this.clientId = clientId;
  this.client = null; // Set to null so the loader is shown.

  this.refreshClientDetails();
  this.checkClientAccess_();
};


NavigatorController.prototype.refreshClientDetails = function() {
  var url = 'clients/' + this.clientId;
  this.grrApiService_.get(url).then(this.onClientDetailsFetched_.bind(this));
};

/**
 * Called when the client details were fetched.
 *
 * @param {Object} response
 * @private
 */
NavigatorController.prototype.onClientDetailsFetched_ = function(response) {
  this.client = response['data']['client'];
};

/**
 * Checks client access.
 *
 * @private
 */
NavigatorController.prototype.checkClientAccess_ = function() {
  this.grrApiService_.head('clients/' + this.clientId + '/flows').then(
      function resolve() {
        this.hasClientAccess = true;
      }.bind(this),
      function reject() {
        this.hasClientAccess = false;
      }.bind(this));
};


/**
 * Directive for the navigator.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.sidebar.navigatorDirective.NavigatorDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/sidebar/navigator.html',
    controller: NavigatorController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.sidebar.navigatorDirective.NavigatorDirective
    .directive_name = 'grrNavigator';


});  // goog.scope
