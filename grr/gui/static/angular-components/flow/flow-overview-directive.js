'use strict';

goog.provide('grrUi.flow.flowOverviewDirective.FlowOverviewController');
goog.provide('grrUi.flow.flowOverviewDirective.FlowOverviewDirective');
goog.require('grrUi.core.utils.stripAff4Prefix');

goog.scope(function() {


var stripAff4Prefix = grrUi.core.utils.stripAff4Prefix;


/**
 * Controller for FlowOverviewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.flow.flowOverviewDirective.FlowOverviewController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.flowUrn;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.flow;

  /** @export {string} */
  this.flowId;

  this.scope_.$watch('flowUrn', this.onFlowUrnChange.bind(this));
};

var FlowOverviewController =
    grrUi.flow.flowOverviewDirective.FlowOverviewController;


/**
 * Handles flowUrn attribute changes.
 *
 * @param {string} newFlowUrn
 * @export
 */
FlowOverviewController.prototype.onFlowUrnChange = function(newFlowUrn) {
  this.flow = null;

  if (angular.isDefined(newFlowUrn)) {
    var flowUrnComponents = stripAff4Prefix(newFlowUrn).split('/');
    var clientId = flowUrnComponents[0];
    this.flowId = flowUrnComponents[flowUrnComponents.length - 1];

    var path = ['clients', clientId, 'flows', this.flowId].join('/');
    this.grrApiService_.get(path).then(this.onFlowFetched.bind(this));
  }
};


/**
 * Called when flow data was fetched.
 * @param {Object} response Response from the server.
 */
FlowOverviewController.prototype.onFlowFetched = function(response) {
  this.flow = response.data;
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
      flowUrn: '=',
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
