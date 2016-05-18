'use strict';

goog.provide('grrUi.client.hostInfoDirective.HostInfoController');
goog.provide('grrUi.client.hostInfoDirective.HostInfoDirective');

goog.scope(function() {


var OPERATION_POLL_INTERVAL = 1000;


/**
 * Controller for HostInfoDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.client.hostInfoDirective.HostInfoController = function(
    $scope, $interval, grrApiService, grrRoutingService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.clientVersionUrl;

  /** @type {string} */
  this.clientId;

  /** @type {?number} */
  this.clientVersion;

  /** @export {Object} */
  this.client;

  /** @type {boolean} */
  this.clientAccessCheckInProgress = true;

  /** @type {boolean} */
  this.hasClientAccess = false;

  /** @type {?string} */
  this.interrogateOperationId;

  /** @private {!angular.$q.Promise} */
  this.interrogateOperationInterval_;

  this.scope_.$watch('controller.clientVersion',
      this.onClientVersionChange_.bind(this));
  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
  this.scope_.$on('$destroy',
      this.stopMonitorInterrogateOperation_.bind(this));
};

var HostInfoController =
    grrUi.client.hostInfoDirective.HostInfoController;


/**
 * Handles changes to the client id.
 *
 * @param {string} clientId The new value for the client id state param.
 * @private
 */
HostInfoController.prototype.onClientIdChange_ = function(clientId) {
  if (angular.isDefined(clientId)) {
    this.clientId = clientId;
    this.clientVersionUrl = '/clients/' + clientId + '/version-times';
    this.fetchClientDetails_();
    this.checkClientAccess_();
  }
};

/**
 * Handles changes to the client version.
 *
 * @param {?number} newValue
 * @param {?number} oldValue
 * @private
 */
HostInfoController.prototype.onClientVersionChange_ = function(newValue, oldValue) {
  // The first non-undefined value for clientVersion comes from fetchClientDetails_ after
  // fetching the details and setting the clientVersion to the age. This will immediately
  // trigger another call to the server. We can prevent this by requiring the clientVersion
  // to have been set before.
  if (oldValue) {
    this.fetchClientDetails_();
  }
};

/**
 * Fetches the client details.
 *
 * @private
 */
HostInfoController.prototype.fetchClientDetails_ = function() {
  var url = '/clients/' + this.clientId;
  var params = {};
  if (this.clientVersion) {
    params['timestamp'] = this.clientVersion;
  }

  this.grrApiService_.get(url, params).then(function success(response) {
    this.client = response.data['client'];
    this.clientVersion = response.data['client']['age'];
  }.bind(this));
};

/**
 * Checks if user has a permission to access the client.
 *
 * @private
 */
HostInfoController.prototype.checkClientAccess_ = function() {
  this.clientAccessCheckInProgress = true;

  this.grrApiService_.head('clients/' + this.clientId + '/flows').then(
      function resolve() {
        this.hasClientAccess = true;
      }.bind(this),
      function reject() {
        this.hasClientAccess = false;
      }.bind(this)).finally(function() {
        this.clientAccessCheckInProgress = false;
      }.bind(this));
};

/**
 * Requests a client approval.
 *
 * @export
 */
HostInfoController.prototype.requestApproval = function() {
  grr.publish('unauthorized', 'aff4:/' + this.clientId);
};

/**
 * Starts the interrogation of the client.
 *
 * @export
 */
HostInfoController.prototype.interrogate = function() {
  var url = '/clients/' + this.clientId + '/actions/interrogate';

  this.grrApiService_.post(url).then(
      function success(response) {
        this.interrogateOperationId = response['data']['operation_id'];
        this.monitorInterrogateOperation_();
      }.bind(this),
      function failure(response) {
        this.stopMonitorInterrogateOperation_();
      }.bind(this));
};

/**
 * Polls the interrogate operation state.
 *
 * @private
 */
HostInfoController.prototype.monitorInterrogateOperation_ = function() {
  this.interrogateOperationInterval_ = this.interval_(
      this.pollInterrogateOperationState_.bind(this),
      OPERATION_POLL_INTERVAL);
};

/**
 * Polls the state of the interrogate operation.
 *
 * @private
 */
HostInfoController.prototype.pollInterrogateOperationState_ = function() {
  var url = 'clients/' + this.clientId + '/actions/interrogate/' + this.interrogateOperationId;

  this.grrApiService_.get(url).then(
    function success(response) {
      if (response['data']['state'] === 'FINISHED') {
        this.stopMonitorInterrogateOperation_();

        this.clientVersion = null; // Newest.
        this.fetchClientDetails_();
      }
    }.bind(this),
    function failure(response) {
      this.stopMonitorInterrogateOperation_();
    }.bind(this));
};

/**
 * Stop polling for the state of the interrogate operation.
 *
 * @private
 */
HostInfoController.prototype.stopMonitorInterrogateOperation_ = function() {
  this.interrogateOperationId = null;
  this.interval_.cancel(this.interrogateOperationInterval_);
};


/**
 * HostInfoDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.hostInfoDirective.HostInfoDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/host-info.html',
    controller: HostInfoController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.hostInfoDirective.HostInfoDirective.directive_name =
    'grrHostInfo';

});  // goog.scope
