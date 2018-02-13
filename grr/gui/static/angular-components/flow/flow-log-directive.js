'use strict';

goog.module('grrUi.flow.flowLogDirective');
goog.module.declareLegacyNamespace();



/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 20 * 1000;

/**
 * Sets the delay between automatic refreshes of the flow log.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/**
 * Controller for FlowLogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const FlowLogController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?string} */
  this.logsUrl;

  /** @type {number} */
  this.autoRefreshInterval = AUTO_REFRESH_INTERVAL_MS;

  this.scope_.$watchGroup(['flowId', 'apiBasePath'],
                          this.onFlowIdOrBasePathChange_.bind(this));
};



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
exports.FlowLogDirective = function() {
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
exports.FlowLogDirective.directive_name = 'grrFlowLog';
