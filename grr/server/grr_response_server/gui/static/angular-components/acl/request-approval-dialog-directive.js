goog.module('grrUi.acl.requestApprovalDialogDirective');
goog.module.declareLegacyNamespace();

const {stringToList} = goog.require('grrUi.core.utils');



/**
 * Controller for RequestApprovalDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const RequestApprovalDialogController =
    function($scope, $q, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {?string} */
  this.subjectTitle;

  /** @export {Array<string>} */
  this.ccAddresses = [];

  /** @export {Array<string>} */
  this.recentReasons;

  /** @export {string} */
  this.selectedRecentReason;

  /** @export {string} */
  this.approversList;

  /** @export {string} */
  this.reason;

  /** @export {boolean} */
  this.useCcAddresses = true;

  /** @export {boolean} */
  this.keepClientAlive = true;

  this.scope_.$watch('approvalType', this.onApprovalTypeChange_.bind(this));
  this.scope_.$watch('controller.selectedRecentReason',
                     this.onSelectedRecentReasonChange_.bind(this));

  this.grrApiService_.getCached('/config/Email.approval_optional_cc_address')
      .then(this.onCcAddressResponse_.bind(this));
  this.grrApiService_.get('/users/me/approvals/client', {count: 7}).then(
      this.onLatestApprovalsResponse_.bind(this));
};



/**
 * Handles changes in approvalType binding.
 *
 * @param {string} newValue
 * @private
 */
RequestApprovalDialogController.prototype.onApprovalTypeChange_ = function(
    newValue) {
  if (angular.isString(newValue)) {
    this.subjectTitle = (newValue.charAt(0).toUpperCase() +
        newValue.slice(1).replace('-', ' '));
  }
};


/**
 * Handles changes in selectedRecentReason input binding.
 *
 * @param {string} newValue
 * @private
 */
RequestApprovalDialogController.prototype.onSelectedRecentReasonChange_ =
    function(newValue) {
  if (angular.isString(newValue) && newValue) {
    this.reason = newValue;
  }
};


/**
 * Handles API response that returns a list of CC addresses to be
 * used when sending the approval.
 *
 * @param {Object} response
 * @private
 */
RequestApprovalDialogController.prototype.onCcAddressResponse_ = function(
    response) {
  this.ccAddresses = stringToList(response['data']['value']['value']);
};


/**
 * Handles API response that returns a list of recent client approvals
 * that this user had requested.
 *
 * @param {Object} response
 * @private
 */
RequestApprovalDialogController.prototype.onLatestApprovalsResponse_ =
    function(response) {
  this.recentReasons = [];
  var items = response['data']['items'];
  for (var i = 0; i < items.length; ++i) {
    var reason = items[i]['value']['reason']['value'];
    if (this.recentReasons.indexOf(reason) === -1) {
      this.recentReasons.push(reason);
    }
  }
};


/**
 * Sends an approval creation request to the server.
 *
 * @return {!angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
RequestApprovalDialogController.prototype.proceed = function() {
  var deferred = this.q_.defer();

  var url = this.scope_['createRequestUrl'];
  var args = angular.copy(this.scope_['createRequestArgs']);
  args['approval']['reason'] = this.reason;
  args['approval']['notified_users'] = stringToList(this.approversList);
  if (this.useCcAddresses && this.ccAddresses) {
    args['approval']['email_cc_addresses'] = this.ccAddresses;
  }
  if (this.scope_['approvalType'] === 'client' && this.keepClientAlive) {
    args['keep_client_alive'] = true;
  }

  this.grrApiService_.post(url, args).then(
      function success() {
        deferred.resolve('Approval request was sent.');
      }, function failure(response) {
        deferred.reject(response['data']['message']);
      });

  return deferred.promise;
};


/**
 * Directive that displays "request approval" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.RequestApprovalDialogDirective = function() {
  return {
    scope: {
      approvalType: '=',
      createRequestUrl: '=',
      createRequestArgs: '=',
      accessErrorDescription: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/' +
        'request-approval-dialog.html',
    controller: RequestApprovalDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.RequestApprovalDialogDirective.directive_name =
    'grrRequestApprovalDialog';
