'use strict';

goog.module('grrUi.flow.flowOverviewDirective');
goog.module.declareLegacyNamespace();


/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 15 * 1000;

/**
 * Sets the delay between automatic refreshes of the flow overview.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/**
 * Controller for FlowOverviewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const FlowOverviewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.flow;

  /** @private {!angular.$q.Promise|undefined} */
  this.pollPromise_;

  this.scope_.$on('$destroy', function() {
    this.grrApiService_.cancelPoll(this.pollPromise_);
  }.bind(this));

  this.scope_.$watchGroup(['flowId', 'apiBasePath'],
                          this.startPolling.bind(this));
};



/**
 * Start polling for flow data.
 *
 * @export
 */
FlowOverviewController.prototype.startPolling = function() {
  this.grrApiService_.cancelPoll(this.pollPromise_);
  this.pollPromise_ = undefined;

  if (angular.isDefined(this.scope_['apiBasePath']) &&
      angular.isDefined(this.scope_['flowId'])) {
    var flowUrl = this.scope_['apiBasePath'] + '/' + this.scope_['flowId'];
    var interval = AUTO_REFRESH_INTERVAL_MS;

    // It's important to assign the result of the poll() call, not the
    // result of the poll().then() call, since we need the original
    // promise to pass to cancelPoll if needed.
    this.pollPromise_ = this.grrApiService_.poll(flowUrl, interval);
    this.pollPromise_.then(
        undefined,
        undefined,
        function notify(response) {
          this.flow = response['data'];
        }.bind(this));
  }
};


/**
 * Directive for displaying log records of a flow with a given URN.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.FlowOverviewDirective = function() {
  return {
    scope: {
      flowId: '=',
      apiBasePath: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-overview.html',
    controller: FlowOverviewController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowOverviewDirective.directive_name = 'grrFlowOverview';
