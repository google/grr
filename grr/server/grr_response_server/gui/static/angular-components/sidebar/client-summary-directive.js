goog.module('grrUi.sidebar.clientSummaryDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const timeService = goog.requireType('grrUi.core.timeService');



/**
 * Controller for ClientSummaryDirective.
 * @unrestricted
 */
const ClientSummaryController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @param {!timeService.TimeService} grrTimeService
   * @ngInject
   */
  constructor($scope, grrApiService, grrTimeService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!timeService.TimeService} */
    this.grrTimeService_ = grrTimeService;

    /** @type {string} */
    this.approvalReason;

    /** @type {Object} */
    this.lastIP;

    /** @type {?number} */
    this.crashTime;

    this.scope_.$watch('client', this.onClientChange_.bind(this));
  }

  /**
   * Handles changes to the client.
   *
   * @private
   */
  onClientChange_() {
    if (!this.scope_['client']) {
      return;
    }

    // Check for the last crash.
    if (this.scope_['client']['value']['last_crash_at']) {
      var currentTimeMs = this.grrTimeService_.getCurrentTimeMs();
      var crashTime = this.scope_['client']['value']['last_crash_at']['value'];
      if (angular.isDefined(crashTime) &&
          (currentTimeMs / 1000 - crashTime / 1000000) < 60 * 60 * 24) {
        this.crashTime = crashTime;
      }
    }

    var clientId = this.scope_['client']['value']['client_id']['value'];
    var lastIPUrl = 'clients/' + clientId + '/last-ip';
    this.grrApiService_.get(lastIPUrl).then(function(response) {
      this.lastIP = response.data;
    }.bind(this));

    var approvalUrl = 'users/me/approvals/client/' + clientId;
    this.grrApiService_.get(approvalUrl).then(function(response) {
      var approvals = response.data['items'];
      if (approvals && approvals.length) {
        // Approvals are returned from newest to oldest, so the first item
        // holds the most recent approval reason.
        this.approvalReason = approvals[0]['value']['reason']['value'];
      }
    }.bind(this));
  }
};



/**
 * Directive for displaying a client summary for the navigation.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ClientSummaryDirective = function() {
  return {
    scope: {client: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/sidebar/client-summary.html',
    controller: ClientSummaryController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ClientSummaryDirective.directive_name = 'grrClientSummary';
