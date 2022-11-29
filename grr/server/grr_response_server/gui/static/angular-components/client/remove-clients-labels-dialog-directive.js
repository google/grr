goog.module('grrUi.client.removeClientsLabelsDialogDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for RemoveClientsLabelsDialogDirective.
 * @unrestricted
 */
const RemoveClientsLabelsDialogController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$q} $q
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, $q, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$q} */
    this.q_ = $q;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @export {Array<string>} */
    this.availableLabels = [];

    /** @export {?string} */
    this.labelName;

    this.scope_.$watch('clients', this.onClientsChange_.bind(this));
  }

  /**
   * Handles changes in the list of clients to strip the label from. Updates
   * the list of available labels.
   *
   * @param {Array<Object>} newValue Updated list of clients.
   * @private
   */
  onClientsChange_(newValue) {
    const labelsSet = {};

    if (angular.isDefined(newValue)) {
      angular.forEach(newValue, function(client) {
        if (angular.isDefined(client['value']['labels'])) {
          angular.forEach(client['value']['labels'], function(label) {
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
  }

  /**
   * Sends /clients/labels/remove request to the server with the list of
   * clients and labels to be removed.
   *
   * @return {!angular.$q.Promise} A promise indicating success or failure.
   * @export
   */
  proceed() {
    const clients = [];
    angular.forEach(this.scope_['clients'], function(clientObj) {
      clients.push(clientObj['value']['client_id']['value']);
    });

    const deferred = this.q_.defer();
    const url = '/clients/labels/remove';
    const params = {client_ids: clients, labels: [this.labelName]};
    this.grrApiService_.post(url, params)
        .then(
            function success() {
              deferred.resolve('Label was successfully removed.');
            }.bind(this),
            function failure(response) {
              deferred.reject(response.data.message);
            }.bind(this));
    return deferred.promise;
  }
};



/**
 * Directive that displays "remove clients labels" dialog.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.RemoveClientsLabelsDialogDirective = function() {
  return {
    scope: {clients: '='},
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
exports.RemoveClientsLabelsDialogDirective.directive_name =
    'grrRemoveClientsLabelsDialog';
