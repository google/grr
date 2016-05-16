'use strict';

goog.provide('grrUi.sidebar.clientSummaryDirective.ClientSummaryController');
goog.provide('grrUi.sidebar.clientSummaryDirective.ClientSummaryDirective');

goog.scope(function() {

/**
 * Controller for ClientSummaryDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @ngInject
 */
grrUi.sidebar.clientSummaryDirective.ClientSummaryController =
    function($scope, grrApiService, grrTimeService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.timeService.TimeService} */
  this.grrTimeService_ = grrTimeService;

  /** @type {string} */
  this.approvalReason;

  /** @type {Object} */
  this.lastIP;

  /** @type {?number} */
  this.crashTime;

  this.scope_.$watch('client', this.onClientChange_.bind(this));
};

var ClientSummaryController =
    grrUi.sidebar.clientSummaryDirective.ClientSummaryController;


/**
 * Handles changes to the client.
 *
 * @private
 */
ClientSummaryController.prototype.onClientChange_ = function() {
  if (!this.scope_['client'])  {
    return;
  }

  // Check for the last crash.
  if (this.scope_['client']['value']['last_crash_at']){
    var currentTimeMs = this.grrTimeService_.getCurrentTimeMs();
    var crashTime = this.scope_['client']['value']['last_crash_at']['value'];
    if (angular.isDefined(crashTime) &&
        (currentTimeMs / 1000 - crashTime / 1000000) < 60 * 60 * 24) {
      this.crashTime = crashTime;
    }
  }

  var clientUrn = this.scope_['client']['value']['urn']['value'];
  var clientId = clientUrn.split('/')[1];

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
};


/**
 * Directive for displaying a client summary for the navigation.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.sidebar.clientSummaryDirective.ClientSummaryDirective = function() {
  return {
    scope: {
      client: '='
    },
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
grrUi.sidebar.clientSummaryDirective.ClientSummaryDirective
    .directive_name = 'grrClientSummary';

});  // goog.scope
