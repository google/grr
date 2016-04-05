'use strict';

goog.provide('grrUi.client.removeClientsLabelsDialogDirective.RemoveClientsLabelsDialogController');
goog.provide('grrUi.client.removeClientsLabelsDialogDirective.RemoveClientsLabelsDialogDirective');

goog.scope(function() {


/**
 * Controller for RemoveClientsLabelsDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.removeClientsLabelsDialogDirective
    .RemoveClientsLabelsDialogController =
    function($scope, grrApiService) {
      /** @private {!angular.Scope} */
      this.scope_ = $scope;

      /** @private {!grrUi.core.apiService.ApiService} */
      this.grrApiService_ = grrApiService;

      /** @export {Array<string>} */
      this.availableLabels = [];

      /** @export {?string} */
      this.labelName;

      /** @export {?string} */
      this.error;

      /** @export {?string} */
      this.success;

      this.scope_.$watch('clients', this.onClientsChange_.bind(this));
    };

var RemoveClientsLabelsDialogController =
    grrUi.client.removeClientsLabelsDialogDirective
    .RemoveClientsLabelsDialogController;


/**
 * Handles changes in the list of clients to strip the label from. Updates
 * the list of available labels.
 *
 * @param {Array<Object>} newValue Updated list of clients.
 * @private
 */
RemoveClientsLabelsDialogController.prototype.onClientsChange_ = function(
    newValue) {
  var labelsSet = {};

  if (angular.isDefined(newValue)) {
    angular.forEach(newValue, function(client) {
      if (angular.isDefined(client['value']['labels'])) {
        angular.forEach(
            client['value']['labels'],
            function(label) {
              // Don't show system labels (i.e. the ones where "GRR" is the
              // owner).
              if (label['value']['owner']['value'] !== 'GRR') {
                labelsSet[label['value']['name']['value']] = true;
              }
            });
      }
    }.bind(this));
  }

  this.availableLabels = Object.keys(labelsSet);
  if (this.availableLabels.length > 0) {
    this.labelName = this.availableLabels[0];
  }
};


/**
 * Sends /clients/labels/remove request to the server with the list of
 * clients and labels to be removed.
 *
 * @export
 */
RemoveClientsLabelsDialogController.prototype.proceed = function() {
  var clients = [];
  angular.forEach(this.scope_.clients, function(clientObj) {
    clients.push(clientObj['value']['urn']['value']);
  });

  this.grrApiService_.post(
      '/clients/labels/remove',
      {client_ids: clients, labels: [this.labelName]}).then(
          function success() {
            this.success = 'Label was successfully removed.';
          }.bind(this),
          function failure(response) {
            this.error = response.data.message;
          }.bind(this));
};


/**
 * Directive that displays "remove clients labels" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.client.removeClientsLabelsDialogDirective
    .RemoveClientsLabelsDialogDirective = function() {
      return {
        scope: {
          clients: '=',
          dismiss: '&',
          close: '&'
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/client/' +
            'remove-clients-labels-dialog.html',
        controller: RemoveClientsLabelsDialogController,
        controllerAs: 'controller'
      };
    };


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.removeClientsLabelsDialogDirective
    .RemoveClientsLabelsDialogDirective
    .directive_name = 'grrRemoveClientsLabelsDialog';


});
