goog.module('grrUi.client.hostInfoDirective');
goog.module.declareLegacyNamespace();



var OPERATION_POLL_INTERVAL_MS = 1000;


/**
 * Controller for HostInfoDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @param {!grrUi.acl.aclDialogService.AclDialogService} grrAclDialogService
 * @param {!grrUi.core.dialogService.DialogService} grrDialogService
 * @ngInject
 */
const HostInfoController = function(
    $scope, $interval, grrApiService, grrRoutingService, grrAclDialogService,
    grrDialogService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @private {!grrUi.acl.aclDialogService.AclDialogService} */
  this.grrAclDialogService_ = grrAclDialogService;

  /** @private {!grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;

  /** @type {string} */
  this.clientVersionUrl;

  /** @type {string} */
  this.clientId;

  /** @type {?number} */
  this.clientVersion;

  /** @export {Object} */
  this.client;

  /** @type {boolean} */
  this.hasClientAccess;

  /** @type {number} */
  this.fetchDetailsRequestId = 0;

  /** @type {?string} */
  this.interrogateOperationId;

  /** @private {!angular.$q.Promise} */
  this.interrogateOperationInterval_;

  // clientId may be inferred from the URL or passed explicitly as
  // a parameter.
  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'clientId',
      this.onClientIdChange_.bind(this));
  this.scope_.$watch('clientId', this.onClientIdChange_.bind(this));

  this.scope_.$watch('controller.clientVersion',
      this.onClientVersionChange_.bind(this));
  // TODO(user): use grrApiService.poll for polling.
  this.scope_.$on('$destroy',
      this.stopMonitorInterrogateOperation_.bind(this));
};



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
  }
};

/**
 * Handles changes to the client version.
 *
 * @param {?number} newValue
 * @private
 */
HostInfoController.prototype.onClientVersionChange_ = function(newValue) {
  if (angular.isUndefined(newValue)) {
    return;
  }

  if (angular.isUndefined(this.client) ||
      this.client['value']['age']['value'] !== newValue) {
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

  this.fetchDetailsRequestId += 1;
  var requestId = this.fetchDetailsRequestId;
  this.grrApiService_.get(url, params).then(function success(response) {
    // Make sure that the request that we got corresponds to the
    // arguments we used while sending it. This is needed for cases
    // when bindings change so fast that we send multiple concurrent
    // requests.
    if (this.fetchDetailsRequestId != requestId) {
      return;
    }

    this.client = response.data;
    this.clientVersion = response.data['value']['age']['value'];
  }.bind(this));
};

/**
 * Requests a client approval.
 *
 * @export
 */
HostInfoController.prototype.requestApproval = function() {
  this.grrAclDialogService_.openRequestClientApprovalDialog(this.clientId);
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
      OPERATION_POLL_INTERVAL_MS);
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
 * Handles clicks on full details history buttons.
 *
 * @param {string} fieldPath Path to a value field of interest.
 * @export
 */
HostInfoController.prototype.showHistoryDialog = function(
    fieldPath) {
  this.grrDialogService_.openDirectiveDialog(
      'grrHostHistoryDialog',
      {
        clientId: this.clientId,
        fieldPath: fieldPath
      },
      {
        windowClass: 'high-modal'
      });
};

/**
 * HostInfoDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.HostInfoDirective = function() {
  return {
    scope: {
      'clientId': '=',
      'readOnly': '='
    },
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
exports.HostInfoDirective.directive_name = 'grrHostInfo';
