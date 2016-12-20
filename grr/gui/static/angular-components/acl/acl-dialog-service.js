'use strict';

goog.provide('grrUi.acl.aclDialogService.AclDialogService');
goog.require('grrUi.acl.requestApprovalDialogDirective.RequestApprovalDialogDirective');

goog.scope(function() {


/**
 * Service for acl dialogs.
 *
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @constructor
 * @ngInject
 * @export
 */
grrUi.acl.aclDialogService.AclDialogService = function(grrDialogService) {
  /** @private {grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;
};

var AclDialogService = grrUi.acl.aclDialogService.AclDialogService;


/**
 * Name of the service in Angular.
 */
AclDialogService.service_name = 'grrAclDialogService';


/**
 * Shows a "request an approval" dialog.
 *
 * @param {string} approvalType Approval type. May be 'client', 'hunt' or
 *     'cron-job'.
 * @param {string} createRequestUrl Url that should be used to send "create
 *     approval request" request.
 * @param {!Object} createRequestArgs Prefilled ApiCreate*ApprovalArgs request.
 * @param {string=} opt_accessErrorDescription If provided this description
 *     will be shown to the user. Its goal is to explain while the user
 *     doesn't have access to the resource.
 *
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
AclDialogService.prototype.openRequestApprovalDialog = function(
    approvalType, createRequestUrl, createRequestArgs,
    opt_accessErrorDescription) {

  // TODO(user): get rid of jQuery here and reimplement in cleaner fashion
  // (all modals should run through our own service, so that we can control
  // their stacking behavior).
  //
  // Handle AngularJS modals.
  $('.modal-dialog:visible').each(function() {
    $(this).scope()['$parent']['$dismiss']();
  });

  var directive =
      grrUi.acl.requestApprovalDialogDirective.RequestApprovalDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, {
    approvalType: approvalType,
    createRequestUrl: createRequestUrl,
    createRequestArgs: createRequestArgs,
    accessErrorDescription: opt_accessErrorDescription
  });
};


/**
 * Shows a "request client approval" dialog.
 *
 * @param {string} clientId Id of a client to request an approval for.
 * @param {string=} opt_accessErrorDescription If provided this description
 *     will be shown to the user. Its goal is to explain while the user
 *     doesn't have access to the resource.
 *
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
AclDialogService.prototype.openRequestClientApprovalDialog = function(
    clientId, opt_accessErrorDescription) {
  return this.openRequestApprovalDialog(
      'client',
      '/users/me/approvals/client/' + clientId,
      {
        client_id: clientId,
        approval: {
        }
      },
      opt_accessErrorDescription);
};

/**
 * Shows a "request hunt approval" dialog.
 *
 * @param {string} huntId Id of a hunt to request an approval for.
 * @param {string=} opt_accessErrorDescription If provided this description
 *     will be shown to the user. Its goal is to explain while the user
 *     doesn't have access to the resource.
 *
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
AclDialogService.prototype.openRequestHuntApprovalDialog = function(
    huntId, opt_accessErrorDescription) {
  return this.openRequestApprovalDialog(
      'hunt',
      '/users/me/approvals/hunt/' + huntId,
      {
        hunt_id: huntId,
        approval: {
        }
      },
      opt_accessErrorDescription);
};

/**
 * Shows a "request cron job approval" dialog.
 *
 * @param {string} cronJobId Id of a cron job to request an approval for.
 * @param {string=} opt_accessErrorDescription If provided this description
 *     will be shown to the user. Its goal is to explain while the user
 *     doesn't have access to the resource.
 *
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
AclDialogService.prototype.openRequestCronJobApprovalDialog = function(
    cronJobId, opt_accessErrorDescription) {
  return this.openRequestApprovalDialog(
      'cron-job',
      '/users/me/approvals/cron-job/' + cronJobId,
      {
        cron_job_id: cronJobId,
        approval: {
        }
      },
      opt_accessErrorDescription);
};

});
