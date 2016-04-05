'use strict';

goog.provide('grrUi.client.clientsListDirective.ClientsListController');
goog.provide('grrUi.client.clientsListDirective.ClientsListDirective');

goog.scope(function() {



/**
 * Controller for ClientsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @ngInject
 */
grrUi.client.clientsListDirective.ClientsListController = function(
    $scope, $modal) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /**
   * This variable is bound to grr-infinite-table's trigger-update attribute
   * and therefore is set but that directive to a function that triggers
   * table update.
   * @export {function()}
   */
  this.triggerUpdate;

  /** @export {Object.<string, Object>} */
  this.clients = {};

  /** @export {Object.<string, boolean>} */
  this.selectedClients = {};

  /** @export {boolean} */
  this.allClientsSelected = false;

  /** @export {number} */
  this.numSelectedClients = 0;

  this.scope_.$watch('query', this.triggerUpdate);
};

var ClientsListController = grrUi.client.clientsListDirective
    .ClientsListController;


/**
 * Handles a click on a table row.
 *
 * @param {Object} client
 * @export
 */
ClientsListController.prototype.onClientClick = function(client) {
  grr.state.client_id = client['value']['urn']['value'];

  grr.publish('hash_state', 'c', client['value']['urn']['value']);

  // Clear the authorization for new clients.
  grr.publish('hash_state', 'reason', '');
  grr.state.reason = '';

  grr.publish('hash_state', 'main', null);
  grr.publish('client_selection', client['value']['urn']['value']);
};


/**
 * Updates number of selected clients by traversing selectedClients dictionary.
 *
 * @export
 */
ClientsListController.prototype.updateNumSelectedClients = function() {
  var count = 0;
  for (var key in this.selectedClients) {
    if (this.selectedClients[key]) {
      ++count;
    }
  }

  this.numSelectedClients = count;
};


/**
 * Handles response from the server with a list of clients corresponding
 * to a query. This function is used in the items provider. It's a  pass-through
 * function - i.e. it doesn't modify the fetched list of clients, but rather
 * updates "clients" and "selectedClients" data structures with incoming data.
 *
 * @param {!Array<Object>} items Incoming clients.
 * @return {!Array<Object>} Clients list.
 * @export
 */
ClientsListController.prototype.onClientsFetched = function(items) {
  angular.forEach(items, function(item) {
    var urn = item['value']['urn']['value'];
    this.clients[urn] = item;
    this.selectedClients[urn] = false;

    item['_mac_addresses'] = [];
    angular.forEach(item['value']['interfaces'], function(iface) {
      if (angular.isDefined(iface['value']['mac_address'])) {
        item['_mac_addresses'].push(iface['value']['mac_address']);
      }
    }.bind(this));

    item['_usernames'] = [];
    angular.forEach(item['value']['users'], function(user) {
      item['_usernames'].push(user['value']['username']);
    }.bind(this));
  }.bind(this));

  return items;
};


/**
 * Selects all the clients in the table
 *
 * @export
 */
ClientsListController.prototype.selectAll = function() {
  for (var key in this.selectedClients) {
    this.selectedClients[key] = this.allClientsSelected;
  }

  this.updateNumSelectedClients();
};


/**
 * Shows label dialog for a given label action.
 *
 * @param {string} action Action can be either 'add' or 'remove'.
 * @export
 */
ClientsListController.prototype.showLabelsDialog = function(action) {
  var clients = [];
  for (var clientUrn in this.selectedClients) {
    if (this.selectedClients[clientUrn]) {
      clients.push(this.clients[clientUrn]);
    }
  }

  var modalScope = this.scope_.$new();
  modalScope.clients = clients;

  var modalInstance;
  if (action == 'add') {
    modalInstance = this.modal_.open({
      template: '<grr-add-clients-labels-dialog ' +
          'clients="clients" ' +
          'close="$close()" ' +
          'dismiss="$dismiss()" />',
      scope: modalScope
    });
  } else if (action == 'remove') {
    modalInstance = this.modal_.open({
      template: '<grr-remove-clients-labels-dialog ' +
          'clients="clients" ' +
          'close="$close()" ' +
          'dismiss="$dismiss()" />',
      scope: modalScope
    });
  } else {
    throw Error('Unexpected action: ' + action);
  }

  this.scope_.$on('$destroy', function() {
    modalScope.$destroy();
  });

  modalInstance.result.then(function resolve() {
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    // Do nothing.
  }.bind(this));
};


/**
 * @export {string}
 * @const
 */
ClientsListController.prototype.clientsQueryUrl =
    '/clients';



/**
 * Displays a table of clients.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.clientsListDirective.ClientsListDirective = function() {
  return {
    scope: {
      query: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/client/clients-list.html',
    controller: ClientsListController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.client.clientsListDirective.ClientsListDirective.directive_name =
    'grrClientsList';

});  // goog.scope
