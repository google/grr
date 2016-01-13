'use strict';

goog.provide('grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogController');
goog.provide('grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective');

goog.scope(function() {


/**
 * Controller for AddClientsLabelsDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogController =
    function($scope, grrApiService) {
      /** @private {!angular.Scope} */
      this.scope_ = $scope;

      /** @private {!grrUi.core.apiService.ApiService} */
      this.grrApiService_ = grrApiService;

      /** @export {?string} */
      this.labelName;

      /** @export {?string} */
      this.error;

      /** @export {?string} */
      this.success;
    };

var AddClientsLabelsDialogController =
    grrUi.client.addClientsLabelsDialogDirective
    .AddClientsLabelsDialogController;


/**
 * Sends /label/add request to the server.
 *
 * @export
 */
AddClientsLabelsDialogController.prototype.proceed = function() {
  var clients = [];
  angular.forEach(this.scope_.clients, function(clientObj) {
    clients.push(clientObj['value']['urn']['value']);
  });

  this.grrApiService_.post(
      '/clients/labels/add',
      {client_ids: clients, labels: [this.labelName]}).then(
          function success() {
            this.success = 'Label was successfully added.';
          }.bind(this),
          function failure(response) {
            this.error = response.data.message;
          }.bind(this));
};


/**
 * Directive that displays "add clients labels" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective =
    function() {
      return {
        scope: {
          clients: '=',
          dismiss: '&',
          close: '&'
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/client/' +
            'add-clients-labels-dialog.html',
        controller: AddClientsLabelsDialogController,
        controllerAs: 'controller'
      };
    };


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective
    .directive_name = 'grrAddClientsLabelsDialog';


});
