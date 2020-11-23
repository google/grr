goog.module('grrUi.client.clientDialogService');
goog.module.declareLegacyNamespace();

const dialogService = goog.requireType('grrUi.core.dialogService');
const {AddClientsLabelsDialogDirective} = goog.require('grrUi.client.addClientsLabelsDialogDirective');
const {RemoveClientsLabelsDialogDirective} = goog.require('grrUi.client.removeClientsLabelsDialogDirective');



/**
 * Service for client dialogs.
 * @export
 * @unrestricted
 */
exports.ClientDialogService = class {
  /**
   * @param {dialogService.DialogService} grrDialogService
   * @ngInject
   */
  constructor(grrDialogService) {
    /** @private {dialogService.DialogService} */
    this.grrDialogService_ = grrDialogService;
  }

  /**
   * Shows an add client label dialog.
   *
   * @param {Array} clients The array of affected clients.
   * @return {angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  openAddClientLabels(clients) {
    var directive = AddClientsLabelsDialogDirective;
    return this.grrDialogService_.openDirectiveDialog(
        directive.directive_name, {clients: clients});
  }

  /**
   * Shows a remove client label dialog.
   *
   * @param {Array} clients The array of affected clients.
   * @return {angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  openRemoveClientLabels(clients) {
    var directive = RemoveClientsLabelsDialogDirective;
    return this.grrDialogService_.openDirectiveDialog(
        directive.directive_name, {clients: clients});
  }
};

var ClientDialogService = exports.ClientDialogService;


/**
 * Name of the service in Angular.
 */
ClientDialogService.service_name = 'grrClientDialogService';
