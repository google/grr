goog.provide('grrUi.acl.module');
goog.require('grrUi.acl.aclDialogService.AclDialogService');
goog.require('grrUi.acl.approvalInfoDirective.ApprovalInfoDirective');
goog.require('grrUi.acl.clientApprovalViewDirective.ClientApprovalViewDirective');
goog.require('grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective');
goog.require('grrUi.acl.grantAccessDirective.GrantAccessDirective');
goog.require('grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective');
goog.require('grrUi.acl.requestApprovalDialogDirective.RequestApprovalDialogDirective');

/**
 * Angular module for acl GRR UI components.
 */
grrUi.acl.module = angular.module('grrUi.acl', ['grrUi.core']);

grrUi.acl.module.service(
    grrUi.acl.aclDialogService.AclDialogService.service_name,
    grrUi.acl.aclDialogService.AclDialogService);

grrUi.acl.module.directive(
    grrUi.acl.approvalInfoDirective.ApprovalInfoDirective.directive_name,
    grrUi.acl.approvalInfoDirective.ApprovalInfoDirective);
grrUi.acl.module.directive(
    grrUi.acl.clientApprovalViewDirective.ClientApprovalViewDirective.directive_name,
    grrUi.acl.clientApprovalViewDirective.ClientApprovalViewDirective);
grrUi.acl.module.directive(
    grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective.directive_name,
    grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective);
grrUi.acl.module.directive(
    grrUi.acl.grantAccessDirective.GrantAccessDirective.directive_name,
    grrUi.acl.grantAccessDirective.GrantAccessDirective);
grrUi.acl.module.directive(
    grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective.directive_name,
    grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective);
grrUi.acl.module.directive(
    grrUi.acl.requestApprovalDialogDirective.RequestApprovalDialogDirective.directive_name,
    grrUi.acl.requestApprovalDialogDirective.RequestApprovalDialogDirective);
