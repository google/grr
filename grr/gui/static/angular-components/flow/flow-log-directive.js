'use strict';

goog.provide('grrUi.flow.flowLogDirective.FlowLogController');
goog.provide('grrUi.flow.flowLogDirective.FlowLogDirective');

goog.scope(function() {


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
 * @constructor
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
