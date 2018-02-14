'use strict';

goog.module('grrUi.acl.acl');
goog.module.declareLegacyNamespace();

const {AclDialogService} = goog.require('grrUi.acl.aclDialogService');
const {ApprovalInfoDirective} = goog.require('grrUi.acl.approvalInfoDirective');
const {ClientApprovalViewDirective} = goog.require('grrUi.acl.clientApprovalViewDirective');
const {CronJobApprovalViewDirective} = goog.require('grrUi.acl.cronJobApprovalViewDirective');
const {HuntApprovalViewDirective} = goog.require('grrUi.acl.huntApprovalViewDirective');
const {HuntFromFlowCopyReviewDirective} = goog.require('grrUi.acl.huntFromFlowCopyReviewDirective');
const {HuntFromHuntCopyReviewDirective} = goog.require('grrUi.acl.huntFromHuntCopyReviewDirective');
const {RequestApprovalDialogDirective} = goog.require('grrUi.acl.requestApprovalDialogDirective');
const {UNAUTHORIZED_API_RESPONSE_EVENT} = goog.require('grrUi.core.apiService');

/**
 * Angular module for acl GRR UI components.
 */
exports.aclModule = angular.module('grrUi.acl', ['grrUi.core']);

exports.aclModule.service(AclDialogService.service_name, AclDialogService);

exports.aclModule.directive(
    ApprovalInfoDirective.directive_name, ApprovalInfoDirective);
exports.aclModule.directive(
    ClientApprovalViewDirective.directive_name, ClientApprovalViewDirective);
exports.aclModule.directive(
    CronJobApprovalViewDirective.directive_name, CronJobApprovalViewDirective);
exports.aclModule.directive(
    HuntApprovalViewDirective.directive_name, HuntApprovalViewDirective);
exports.aclModule.directive(
    HuntFromFlowCopyReviewDirective.directive_name,
    HuntFromFlowCopyReviewDirective);
exports.aclModule.directive(
    HuntFromHuntCopyReviewDirective.directive_name,
    HuntFromHuntCopyReviewDirective);
exports.aclModule.directive(
    RequestApprovalDialogDirective.directive_name,
    RequestApprovalDialogDirective);

exports.aclModule.run(function($rootScope, grrAclDialogService) {
  // Listen to UnauthorizedApiResponse events and show the approval
  // dialog when they're fired (see core/api-service.js for the
  // source of the events).
  $rootScope.$on(UNAUTHORIZED_API_RESPONSE_EVENT, function(event, data) {
    grrAclDialogService.openApprovalDialogForSubject(data['subject'], data['reason']);
  });
});
