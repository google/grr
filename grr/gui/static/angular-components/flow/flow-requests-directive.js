'use strict';

goog.module('grrUi.flow.flowRequestsDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for FlowRequestsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const FlowRequestsController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.requestsUrl;

  this.scope_.$watchGroup(['flowId', 'apiBasePath'],
                          this.onFlowIdOrBasePathChange_.bind(this));
};



/**
 * Handles directive's arguments changes.
 *
 * @param {Array<string>} newValues
 * @private
 */
FlowRequestsController.prototype.onFlowIdOrBasePathChange_ = function(
    newValues) {
  if (newValues.every(angular.isDefined)) {
    this.requestsUrl = [this.scope_['apiBasePath'],
                        this.scope_['flowId'],
                        'requests'].join('/');
  }
};


/**
 * Directive for displaying requests of a flow with a given URN.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.FlowRequestsDirective = function() {
  return {
    scope: {
      flowId: '=',
      apiBasePath: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-requests.html',
    controller: FlowRequestsController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowRequestsDirective.directive_name = 'grrFlowRequests';
