'use strict';

goog.module('grrUi.acl.aclDialogService');
goog.module.declareLegacyNamespace();

const {RequestApprovalDialogDirective} = goog.require('grrUi.acl.requestApprovalDialogDirective');
const {stripAff4Prefix} = goog.require('grrUi.core.utils');
/**
 * @fileoverview
 * @suppress {missingProperties}
 */




/**
 * Service for acl dialogs.
 *
 * @param {angular.Scope} $rootScope The Angular root scope.
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @constructor
 * @ngInject
 * @export
 */
exports.AclDialogService = function($rootScope, grrDialogService) {
  /** @private {angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;
};

var AclDialogService = exports.AclDialogService;


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

  var directive = RequestApprovalDialogDirective;
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

/**
 * Shows an "unauthorized approval dialog for a given subject with a given
 * message.
 *
 * @param {string} subject URN of a subject that was denied access to.
 * @param {string} message Message with details about access denial.
 *
 * @export
 */
AclDialogService.prototype.openApprovalDialogForSubject = function(
    subject, message) {
  // TODO(user): get rid of this code as soon as we stop passing
  // information about objects by passing URNs and guessing the
  // object type.
  var components = stripAff4Prefix(subject).split('/');
  if (/^C\.[0-9a-fA-F]{16}$/.test(components[0])) {
    this.openRequestClientApprovalDialog(
        components[0], message);
  } else if (components[0] == 'hunts') {
    this.openRequestHuntApprovalDialog(
        components[1], message);
  } else if (components[0] == 'cron') {
    this.openRequestCronJobApprovalDialog(
        components[1], message);
  } else {
    throw new Error('Can\'t determine type of resources.');
  }
};

