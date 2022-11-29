goog.module('grrUi.client.clientsListDirective');
goog.module.declareLegacyNamespace();

const clientDialogService = goog.requireType('grrUi.client.clientDialogService');
const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for ClientsListDirective.
 * @unrestricted
 */
const ClientsListController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!clientDialogService.ClientDialogService}
   *     grrClientDialogService
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrClientDialogService, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!routingService.RoutingService} */
    this.grrRoutingService_ = grrRoutingService;

    /** @private {!clientDialogService.ClientDialogService} */
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

    /**
     * A suggested approval reason, to be included in links to clients.
     * @private {string}
     */
    this.suggestedReason;

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, 'q', this.onQueryChange_.bind(this));

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, 'reason', (reason) => {
          this.suggestedReason = reason;
        });
  }

  /**
   * Handles changes to the query.
   *
   * @param {string} query The new value for the q param.
   * @private
   */
  onQueryChange_(query) {
    this.query = query;
    if (this.triggerUpdate) {
      this.triggerUpdate();
    }
  }

  /**
   * Handles a click on a table row.
   *
   * @param {Object} client
   * @export
   */
  onClientClick(client) {
    const clientId = client['value']['client_id']['value'];
    this.grrRoutingService_.go('client.hostInfo', {
      clientId: clientId,
      reason: this.suggestedReason,
    });
  }

  /**
   * Updates number of selected clients by traversing selectedClients
   * dictionary.
   *
   * @export
   */
  updateNumSelectedClients() {
    let count = 0;
    for (const key in this.selectedClients) {
      if (this.selectedClients[key]) {
        ++count;
      }
    }

    this.numSelectedClients = count;
  }

  /**
   * Handles response from the server with a list of clients corresponding
   * to a query. This function is used in the items provider. It's a
   * pass-through function - i.e. it doesn't modify the fetched list of clients,
   * but rather updates "clients" and "selectedClients" data structures with
   * incoming data.
   *
   * @param {!Array<Object>} items Incoming clients.
   * @return {!Array<Object>} Clients list.
   * @export
   */
  onClientsFetched(items) {
    angular.forEach(items, function(item) {
      const clientId = item['value']['client_id']['value'];
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
  }

  /**
   * Selects all the clients in the table
   *
   * @export
   */
  selectAll() {
    for (const key in this.selectedClients) {
      this.selectedClients[key] = this.allClientsSelected;
    }

    this.updateNumSelectedClients();
  }

  /**
   * Shows label dialog for a given label action.
   *
   * @param {string} action Action can be either 'add' or 'remove'.
   * @export
   */
  showLabelsDialog(action) {
    const clients = [];
    for (const clientId in this.selectedClients) {
      if (this.selectedClients[clientId]) {
        clients.push(this.clients[clientId]);
      }
    }

    let result;
    if (action == 'add') {
      result = this.grrClientDialogService_.openAddClientLabels(clients);
    } else if (action == 'remove') {
      result = this.grrClientDialogService_.openRemoveClientLabels(clients);
    } else {
      throw Error('Unexpected action: ' + action);
    }

    result.then(
        function resolve() {
          this.triggerUpdate();
        }.bind(this),
        function dismiss() {
          // Do nothing.
        }.bind(this));
  }
};



/**
 * @export {string}
 * @const
 */
ClientsListController.prototype.clientsQueryUrl = '/clients';


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
