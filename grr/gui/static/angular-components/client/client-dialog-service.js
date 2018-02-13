'use strict';

goog.module('grrUi.client.clientDialogService');
goog.module.declareLegacyNamespace();

const {AddClientsLabelsDialogDirective} = goog.require('grrUi.client.addClientsLabelsDialogDirective');
const {RemoveClientsLabelsDialogDirective} = goog.require('grrUi.client.removeClientsLabelsDialogDirective');



/**
 * Service for client dialogs.
 *
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @constructor
 * @ngInject
 * @export
 */
exports.ClientDialogService = function(grrDialogService) {
  /** @private {grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;
};

var ClientDialogService = exports.ClientDialogService;


/**
 * Name of the service in Angular.
 */
ClientDialogService.service_name = 'grrClientDialogService';

/**
 * Shows an add client label dialog.
 *
 * @param {Array} clients The array of affected clients.
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
ClientDialogService.prototype.openAddClientLabels = function(clients) {
  var directive = AddClientsLabelsDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, { clients: clients });
};

/**
 * Shows a remove client label dialog.
 *
 * @param {Array} clients The array of affected clients.
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
ClientDialogService.prototype.openRemoveClientLabels = function(clients) {
  var directive = RemoveClientsLabelsDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, { clients: clients });
};
