goog.module('grrUi.client.clientsListDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ClientsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.client.clientDialogService.ClientDialogService} grrClientDialogService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
const ClientsListController = function(
    $scope, grrClientDialogService, grrRoutingService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @private {!grrUi.client.clientDialogService.ClientDialogService} */
  this.grrClientDialogService_ = grrClientDialogService;

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

  /** @export {string} */
  this.query;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'q',
      this.onQueryChange_.bind(this));
};



/**
 * Handles changes to the query.
 *
 * @param {string} query The new value for the q param.
 * @private
 */
ClientsListController.prototype.onQueryChange_ = function(query) {
  this.query = query;
  if (this.triggerUpdate) {
    this.triggerUpdate();
  }
};

/**
 * Handles a click on a table row.
 *
 * @param {Object} client
 * @export
 */
ClientsListController.prototype.onClientClick = function(client) {
  var clientId = client['value']['client_id']['value'];
  this.grrRoutingService_.go('client', {clientId: clientId});
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
    var clientId = item['value']['client_id']['value'];
    this.clients[clientId] = item;
    this.selectedClients[clientId] = false;

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

    item['tableKey'] = clientId;
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
  for (var clientId in this.selectedClients) {
    if (this.selectedClients[clientId]) {
      clients.push(this.clients[clientId]);
    }
  }

  var result;
  if (action == 'add') {
    result = this.grrClientDialogService_.openAddClientLabels(clients);
  } else if (action == 'remove') {
    result = this.grrClientDialogService_.openRemoveClientLabels(clients);
  } else {
    throw Error('Unexpected action: ' + action);
  }

  result.then(function resolve() {
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
exports.ClientsListDirective = function() {
  return {
    scope: {},
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
exports.ClientsListDirective.directive_name = 'grrClientsList';
