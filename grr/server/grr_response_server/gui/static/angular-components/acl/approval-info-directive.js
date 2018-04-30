'use strict';

goog.module('grrUi.acl.approvalInfoDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');


/**
 * Controller for ApprovalInfoDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const ApprovalInfoController = function(
    $scope, $attrs, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.Attributes} */
  this.attrs_ = $attrs;

  /** @private {!ApiService} */
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
      // Set the out-binding so that other directives in the same
      // template can have access to the approval object. Only do this
      // if out-binding is actually specified.
      if (this.attrs_['approvalObject']) {
        this.scope_['approvalObject'] = response['data'];
      }

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
exports.ApprovalInfoDirective = function() {
  return {
    scope: {
      approvalType: '=',
      username: '=',
      objectId: '=',
      approvalId: '=',

      // Out-binding. Will be set so that other directives can reuse
      // the fetched object.
      approvalObject: '='
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
exports.ApprovalInfoDirective.directive_name = 'grrApprovalInfo';
