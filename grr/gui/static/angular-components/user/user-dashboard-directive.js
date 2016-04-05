'use strict';

goog.provide('grrUi.user.userDashboardDirective.UserDashboardController');
goog.provide('grrUi.user.userDashboardDirective.UserDashboardDirective');


/**
 * Controller for UserDashboardDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.user.userDashboardDirective.UserDashboardController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array<Object>} */
  this.clientApprovals;

  this.grrApiService_.get('/users/me/approvals/client', {count: 7}).then(
      this.onApprovals_.bind(this));
  this.grrApiService_.get('/hunts',
                          {
                            count: 5,
                            active_within: '31d',
                            created_by: 'me'
                          }).then(this.onHunts_.bind(this));
};
var UserDashboardController =
    grrUi.user.userDashboardDirective.UserDashboardController;


/**
 * Handles results of the user approvals request.
 *
 * @param {!Object} response API response.
 * @private
 */
UserDashboardController.prototype.onApprovals_ = function(response) {
  this.clientApprovals = response['data']['items'];
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
 * @param {string} clientUrn Client urn corresponding to a clicked row.
 * @export
 */
UserDashboardController.prototype.onClientClicked = function(clientUrn) {
  // TODO(user): abstract this code away into a service.
  grr.state.client_id = clientUrn;

  grr.publish('hash_state', 'c', clientUrn);

  // Clear the authorization for new clients.
  grr.publish('hash_state', 'reason', '');
  grr.state.reason = '';

  grr.publish('hash_state', 'main', null);
  grr.publish('client_selection', clientUrn);
};

/**
 * Handles clicks in the hunts panel.
 *
 * @param {!Object} hunt Hunt object corresponding to a clicked row.
 * @export
 */
UserDashboardController.prototype.onHuntClicked = function(hunt) {
  grr.publish('hash_state', 'hunt_id', hunt['value']['urn']['value']);
  grr.publish('hash_state', 'main', 'ManageHunts');
  grr.publish('hunt_selection', hunt['value']['urn']['value']);
};


/**
 * UserDashboardDirective renders a dashboard that users see when they
 * hit GRR's Admin UI home page.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.user.userDashboardDirective.UserDashboardDirective =
    function() {
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
grrUi.user.userDashboardDirective.UserDashboardDirective
    .directive_name = 'grrUserDashboard';
