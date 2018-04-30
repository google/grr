'use strict';

goog.module('grrUi.client.addClientsLabelsDialogDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for AddClientsLabelsDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const AddClientsLabelsDialogController = function($scope, $q, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {?string} */
  this.labelName;
};



/**
 * Sends /label/add request to the server.
 *
 * @return {!angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
AddClientsLabelsDialogController.prototype.proceed = function() {
  var clients = [];
  angular.forEach(this.scope_['clients'], function(clientObj) {
    clients.push(clientObj['value']['client_id']['value']);
  });

  var deferred = this.q_.defer();
  var url = '/clients/labels/add';
  var params = {
    client_ids: clients,
    labels: [this.labelName]
  };
  this.grrApiService_.post(url, params).then(
    function success() {
      deferred.resolve('Label was successfully added.');
    }.bind(this),
    function failure(response) {
      deferred.reject(response.data.message);
    }.bind(this));

  return deferred.promise;
};


/**
 * Directive that displays "add clients labels" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.AddClientsLabelsDialogDirective = function() {
  return {
    scope: {
      clients: '='
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
exports.AddClientsLabelsDialogDirective.directive_name =
    'grrAddClientsLabelsDialog';
