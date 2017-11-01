'use strict';

goog.provide('grrUi.semantic.flowIdDirective.FlowIdController');
goog.provide('grrUi.semantic.flowIdDirective.FlowIdDirective');

goog.scope(function() {


/**
 * Controller for FlowIdDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.semantic.flowIdDirective.FlowIdController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.clientId;
};
var FlowIdController = grrUi.semantic.flowIdDirective.FlowIdController;


/**
 * Directive that displays ApiFlowId values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @export
 */
grrUi.semantic.flowIdDirective.FlowIdDirective = function() {
  return {
    scope: {
      value: '='
    },
    require: '?^grrClientContext',
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/flow-id.html',
    controller: FlowIdController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, grrClientContextCtrl) {
      if (grrClientContextCtrl) {
        scope['controller'].clientId = grrClientContextCtrl.clientId;
      }
    }
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.flowIdDirective.FlowIdDirective.directive_name =
    'grrFlowId';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.flowIdDirective.FlowIdDirective.semantic_type =
    'ApiFlowId';


});  // goog.scope
