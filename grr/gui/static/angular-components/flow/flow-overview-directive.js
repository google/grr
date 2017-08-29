'use strict';

goog.provide('grrUi.flow.flowOverviewDirective.FlowOverviewController');
goog.provide('grrUi.flow.flowOverviewDirective.FlowOverviewDirective');
goog.require('grrUi.core.utils.stripAff4Prefix');

goog.scope(function() {


var stripAff4Prefix = grrUi.core.utils.stripAff4Prefix;


/** @const {number} */
grrUi.flow.flowOverviewDirective.AUTO_REFRESH_INTERVAL_S = 15;

/**
 * Controller for FlowOverviewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.flow.flowOverviewDirective.FlowOverviewController = function(
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

var FlowOverviewController =
    grrUi.flow.flowOverviewDirective.FlowOverviewController;


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
    var interval = grrUi.flow.flowOverviewDirective.AUTO_REFRESH_INTERVAL_S
        * 1000;

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
grrUi.flow.flowOverviewDirective.FlowOverviewDirective = function() {
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
grrUi.flow.flowOverviewDirective.FlowOverviewDirective.directive_name =
    'grrFlowOverview';

});  // goog.scope
