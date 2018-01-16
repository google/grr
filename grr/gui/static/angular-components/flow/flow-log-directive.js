'use strict';

goog.provide('grrUi.flow.flowLogDirective.FlowLogController');
goog.provide('grrUi.flow.flowLogDirective.FlowLogDirective');

goog.scope(function() {


/** @const {number} */
grrUi.flow.flowLogDirective.AUTO_REFRESH_INTERVAL_MS = 20 * 1000;


/**
 * Controller for FlowLogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.flowLogDirective.FlowLogController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?string} */
  this.logsUrl;

  /** @type {number} */
  this.autoRefreshInterval =
      grrUi.flow.flowLogDirective.AUTO_REFRESH_INTERVAL_MS;

  this.scope_.$watchGroup(['flowId', 'apiBasePath'],
                          this.onFlowIdOrBasePathChange_.bind(this));
};

var FlowLogController =
    grrUi.flow.flowLogDirective.FlowLogController;


/**
 * Handles flowId attribute changes.
 *
 * @private
 */
FlowLogController.prototype.onFlowIdOrBasePathChange_ = function(newValue) {
  if (angular.isDefined(this.scope_['flowId']) &&
      angular.isDefined(this.scope_['apiBasePath'])) {
    this.logsUrl = [this.scope_['apiBasePath'],
                    this.scope_['flowId'],
                    'log'].join('/');
  }
};


/**
 * Directive for displaying logs of a flow with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.flow.flowLogDirective.FlowLogDirective = function() {
  return {
    scope: {
      flowId: '=',
      apiBasePath: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-log.html',
    controller: FlowLogController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowLogDirective.FlowLogDirective.directive_name = 'grrFlowLog';


});  // goog.scope
