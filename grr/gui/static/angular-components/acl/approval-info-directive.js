'use strict';

goog.provide('grrUi.acl.approvalInfoDirective.ApprovalInfoController');
goog.provide('grrUi.acl.approvalInfoDirective.ApprovalInfoDirective');

goog.require('grrUi.core.apiService.stripTypeInfo');


goog.scope(function() {


var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;


/**
 * Controller for ApprovalInfoDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.acl.approvalInfoDirective.ApprovalInfoController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.fetchUrl;

  /** @type {string} */
  this.grantUrl;

  /** @type {string} */
  this.approvalTypeTitle;

  /** @type {*} */
  this.approvalObject;

  /** @type {boolean} */
  this.requestSent;

  /** @type {string} */
  this.statusMessage;

  this.scope_.$watchGroup(['approvalType', 'objectId', 'approvalId'],
                          this.onParamsChanged_.bind(this));
  this.scope_.$watch('controller.fetchUrl',
                     this.onApprovalFetchUrlChanged_.bind(this));
};
var ApprovalInfoController =
    grrUi.acl.approvalInfoDirective.ApprovalInfoController;


/**
 * Handles changes to directive's params.
 *
 * @private
 */
ApprovalInfoController.prototype.onParamsChanged_ = function() {
  if (angular.isString(this.scope_['approvalType']) &&
      angular.isString(this.scope_['username']) &&
      angular.isString(this.scope_['objectId']) &&
      angular.isString(this.scope_['approvalId'])) {

    this.approvalTypeTitle = this.scope_['approvalType']
        .replace('-', ' ');
    this.fetchUrl = ['users',
                     this.scope_['username'],
                     'approvals',
                     this.scope_['approvalType'],
                     this.scope_['objectId'],
                     this.scope_['approvalId']].join('/');
    this.grantUrl = this.fetchUrl + '/actions/grant';
  }
};

/**
 * Handles changes to the approval's URL (controller.fetchUrl).
 *
 * @private
 */
ApprovalInfoController.prototype.onApprovalFetchUrlChanged_ = function() {
  this.approvalObject = null;

  if (angular.isString(this.fetchUrl)) {
    this.grrApiService_.get(this.fetchUrl).then(function(response) {
      this.approvalObject = stripTypeInfo(response['data']);

      if (this.approvalObject['is_valid']) {
        this.requestSent = true;
        this.statusMessage = 'This approval has already been granted!';
      }
    }.bind(this));
  }
};

/**
 * Handles clicks on the "Approve" button.
 *
 * @export
 */
ApprovalInfoController.prototype.onClick = function() {
  if (!angular.isObject(this.approvalObject)) {
    return;
  }

  this.requestSent = true;
  this.grrApiService_.post(this.grantUrl).then(
      function success() {
        this.statusMessage = 'Approval granted.';
      }.bind(this),
      function failure(response) {
        this.statusMessage = 'FAILURE: ' + response['data']['message'];
      }.bind(this));
};

/**
 * ApprovalInfoDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.acl.approvalInfoDirective.ApprovalInfoDirective = function() {
  return {
    scope: {
      approvalType: '=',
      username: '=',
      objectId: '=',
      approvalId: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/approval-info.html',
    controller: ApprovalInfoController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.acl.approvalInfoDirective.ApprovalInfoDirective.directive_name =
    'grrApprovalInfo';

});  // goog.scope
