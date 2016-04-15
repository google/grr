'use strict';

goog.provide('grrUi.client.clientDialogService.ClientDialogService');
goog.require('grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective');
goog.require('grrUi.client.removeClientsLabelsDialogDirective.RemoveClientsLabelsDialogDirective');

goog.scope(function() {


/**
 * Service for client dialogs.
 *
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @constructor
 * @ngInject
 * @export
 */
grrUi.client.clientDialogService.ClientDialogService =
  function (grrDialogService) {
    /** @private {grrUi.core.dialogService.DialogService} */
    this.grrDialogService_ = grrDialogService;
  };

var ClientDialogService =
    grrUi.client.clientDialogService.ClientDialogService;


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
ClientDialogService.prototype.openAddClientLabels = function(clients){
  var directive = grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, { clients: clients });
};

/**
 * Shows a remove client label dialog.
 *
 * @param {Array} clients The array of affected clients.
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
ClientDialogService.prototype.openRemoveClientLabels = function(clients){
  var directive = grrUi.client.removeClientsLabelsDialogDirective.RemoveClientsLabelsDialogDirective;
  return this.grrDialogService_.openDirectiveDialog(directive.directive_name, { clients: clients });
};

});