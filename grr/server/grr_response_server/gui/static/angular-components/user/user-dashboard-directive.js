goog.module('grrUi.user.userDashboardDirective');
goog.module.declareLegacyNamespace();

const MAX_SHOWN_CLIENTS = 7;

/**
 * This function gets a list of approvals and filters out duplicates.
 * We assume that approvals are already sorted in a reversed-timestamp
 * order. The rules are:
 * 1. In case of equal validity and subject, we prefer the approval
 *    that comes first in the list (meaning this would be the newer approval).
 * 2. In case of equal subject and different validity, we prefer the approval
 *    that is valid.
 *
 * @param {!Array<!Object>} approvals
 * @return {!Array<!Object>} Filtered approvals.
 */
const filterOutDuplicateApprovals = function(approvals) {
  const approvalsMap = {};
  for (const item of approvals) {
    const itemKey = item['value']['subject']['value']['client_id']['value'];
    const prevApproval = approvalsMap[itemKey];

    if (prevApproval) {
      const prevApprovalHasPrecedence = (prevApproval['value']['is_valid']['value'] ||
                                         !item['value']['is_valid']['value']);
      if (prevApprovalHasPrecedence) {
        continue;
      }
    }

    approvalsMap[itemKey] = item;
  }

  const result = [];
  for (const item of approvals) {
    const itemKey = item['value']['subject']['value']['client_id']['value'];
    const selectedApproval = approvalsMap[itemKey];

    if (item['value']['id']['value'] ===
        selectedApproval['value']['id']['value']) {
      result.push(item);
    }
  }

  return result;
};
exports.filterOutDuplicateApprovals = filterOutDuplicateApprovals;

/**
 * Controller for UserDashboardDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
const UserDashboardController = function(
    $scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {Array<Object>} */
  this.clientApprovals;

  // We need at most 7 approvals, but as there may be more
  // than 1 approval for the same client, we fetch 20 and then filter
  // the duplicates out.
  this.grrApiService_.get('/users/me/approvals/client', {count: 20})
      .then(r => this.onClientApprovals_(r));
  this.grrApiService_.get('/hunts',
                          {
                            count: 5,
                            active_within: '31d',
                            created_by: 'me'
                          }).then(r => this.onHunts_(r));
};


/**
 * Handles results of the user approvals request.
 *
 * @param {!Object} response API response.
 * @private
 */
UserDashboardController.prototype.onClientApprovals_ = function(response) {
  this.clientApprovals = filterOutDuplicateApprovals(
      response['data']['items']).slice(0, MAX_SHOWN_CLIENTS);
};


/**
 * Handles results of the hunts request.
 *
 * @param {!Object} response API response.
 * @private
 */
UserDashboardController.prototype.onHunts_ = function(response) {
  this.hunts = response['data']['items'];
};

/**
 * Handles clicks in the client panel.
 *
 * @param {string} clientId Client ID corresponding to a clicked row.
 * @export
 */
UserDashboardController.prototype.onClientClicked = function(clientId) {
  this.grrRoutingService_.go('client', {clientId: clientId});
};

/**
 * Handles clicks in the hunts panel.
 *
 * @param {!Object} hunt Hunt object corresponding to a clicked row.
 * @export
 */
UserDashboardController.prototype.onHuntClicked = function(hunt) {
  var huntId = hunt['value']['urn']['value'].split('/')[2];
  this.grrRoutingService_.go('hunts', {huntId: huntId});
};


/**
 * UserDashboardDirective renders a dashboard that users see when they
 * hit GRR's Admin UI home page.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.UserDashboardDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/user/user-dashboard.html',
    controller: UserDashboardController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.UserDashboardDirective.directive_name = 'grrUserDashboard';
