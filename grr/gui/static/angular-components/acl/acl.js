goog.provide('grrUi.acl.module');
goog.require('grrUi.acl.approvalInfoDirective.ApprovalInfoDirective');
goog.require('grrUi.acl.clientApprovalViewDirective.ClientApprovalViewDirective');
goog.require('grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective');
goog.require('grrUi.acl.grantAccessDirective.GrantAccessDirective');
goog.require('grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective');

/**
 * Angular module for acl GRR UI components.
 */
grrUi.acl.module = angular.module('grrUi.acl', ['grrUi.core']);

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
