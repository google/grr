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

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.flow;

  this.scope_.$watchGroup(['flowId', 'apiBasePath'],
                          this.onFlowIdOrBasePathChange_.bind(this));
};

var FlowOverviewController =
    grrUi.flow.flowOverviewDirective.FlowOverviewController;


/**
 * Handles directive's arguments changes.
 *
 * @param {Array<string>} newValues
 * @private
 */
FlowOverviewController.prototype.onFlowIdOrBasePathChange_ = function(
    newValues) {
  this.flow = null;

  if (newValues.every(angular.isDefined)) {
    var flowUrl = this.scope_['apiBasePath'] + '/' + this.scope_['flowId'];
    this.grrApiService_.get(flowUrl).then(function(response) {
      this.flow = response.data;
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
